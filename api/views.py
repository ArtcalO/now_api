from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny, BasePermission
from django.utils import timezone
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db import transaction
from rest_framework.response import Response
from datetime import datetime, date, timedelta
from django.contrib.auth.models import User, Group
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.filters import SearchFilter
from django.db.models import Sum
from api.serializers import *
from api.models import *

FORBIDEN_OPERATION_MSG = {"status":"Vous n'êtes pas autorisé pour cet opération !"}
DGA = "Directeur d’Agence"
GCHT = "Guichetier"
SU = "Superutilisateur"

def isDGAat(user, agency):
	attribution = Attributions.objects.get(user=user)
	if(attribution.role.name == DGA and attribution.agency==agency):
		return True
	else:
		return False

def checkUserAttribution(user):
	attribution = Attributions.objects.get(user=user)
	return attribution.role.name

class ProvinceViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Province.objects.all()
	serializer_class = ProvinceSerializer

class ImportationViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Importation.objects.all()
	serializer_class = ImportationSerializer

class AnyPayViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = AnyPay.objects.all()
	serializer_class = AnyPaySerializer

	def getCommandesDGA(self):
		dga_attrib=Attributions.objects.filter(role__name=DGA)
		user_dga_tab = [x.user.id for x in dga_attrib]
		sum_comm = Commande.objects\
			.filter(user__id__in=user_dga_tab, confirmed=False, refused=False)\
			.aggregate(Sum('quantity')).get('quantity__sum')
		return sum_comm

	@transaction.atomic()
	@action(methods=["GET"], detail=False, url_name=r"fetch", url_path=r"fetch")
	def fetch(self, request):
		obj=AnyPay.objects.get(id=1)
		main_stock = MainStock.instance()
		total_agencies = Agency.objects\
			.filter(total_amount__gte=0)\
			.aggregate(Sum('cirulating_amount')).get('cirulating_amount__sum')
		total_commandes_dga = self.getCommandesDGA()
		main_stock.total_amount = obj.amount
		main_stock.requested_amount = total_commandes_dga if total_commandes_dga else 0
		main_stock.circulating_amount = total_agencies if total_agencies else 0
		main_stock.available_amount=obj.amount-(main_stock.requested_amount+main_stock.circulating_amount)
		main_stock.last_modified=timezone.now
		main_stock.save()
		return Response({"status":"Anypay fetched succesfully !"},200)

class TokenPairView(TokenObtainPairView):
	serializer_class = TokenPairSerializer

class UserViewset(viewsets.ModelViewSet):
	authentication_classes = JWTAuthentication,SessionAuthentication
	permission_classes = [IsAuthenticated]
	queryset = User.objects.all()
	serializer_class = UserSerializer
	filter_backends = [SearchFilter]
	search_fields = "first_name","last_name","username"

	def list(self, request, *args, **kwargs):
		groups = [x.name for x in request.user.groups.all()]
		if(request.user.is_superuser):
			return super().list(request, *args, **kwargs)
		else:
			self.queryset = self.queryset.filter(id=request.user.id)
			return super().list(request, *args, **kwargs)


class UserExtendedViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = UserExtended.objects.all()
	serializer_class = UserExtendedSerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "user",
	filterset_fields = {
		'user': ['exact',],
		'telephone': ['exact']
	}

	@transaction.atomic()
	def create(self, request):
		data=request.data
		role:Role=Role.objects.get(id=int(data.get('role')))
		agency:Agency=Agency.objects.get(id=int(data.get('agency')))
		guichet=[]
		try:
			guichet:Guichet=Guichet.objects.get(id=int(data.get('guichet')))
		except Exception:
			pass
		user = User(
			username=data.get('user.username'),
			first_name = data.get('user.first_name'),
			last_name = data.get('user.last_name'),
			)
		user.set_password(data.get('user.password'))
		user.save()
		user_extended = UserExtended(
			user=user,
			telephone=data.get('telephone')
			)
		attribution = Attributions(
			user=user,
			agency=agency,
			role=role
			)
		user_extended.save()
		attribution.save()
		if(guichet):
			guichet.guichetier=user
			hist_guichet = HisoriqueGuichet(
				user=user,
				guichet=guichet,
				details=f"Affectation de l'utilisateur {user.first_name} {user.last_name} au guichet n°{guichet.name}"
				)
			hist_guichet.save()
			guichet.save()
		serializer = UserExtendedSerializer(user_extended, many=False).data

		return Response(serializer,201)

	@action(methods=["POST"], detail=True, url_name=r"change-pswd", url_path=r"change-pswd")
	def changeSUPswd(self,request,pk):
		if(checkUserAttribution(request.user)==SU or checkUserAttribution(request.user)==DGA):
			ext_user=self.get_object()
			user = ext_user.user
			user.set_password(request.data.get('password'))
			user.save()
			ext_user.save()
			return Response({"status":"Mot de passe changé avec success !"},200)
		else:
			return Response({'status':"Vous n'êtes pas autorisé !"},405)

	@action(methods=["GET"], detail=False, url_path=r"guichetiers", url_name=r"guichetiers")
	def guichetiers(self,request):
		tab_guichetiers = []
		attributions = Attributions.objects.filter(role__id=2)
		users = UserExtended.objects.all()
		for at in attributions:
			for u in users:
				if u.user.id == at.user.id:
					tab_guichetiers.append(u)
		serializer = UserExtendedSerializer(tab_guichetiers, many=True).data
		return Response(serializer, 200)

	@action(methods=["GET"], detail=False, url_name=r"g-agency", url_path=r"g-agency/(?P<id_agency>\d)")
	def g_agency(self,request,id_agency):
		tab_guichetiers = []
		attributions = Attributions.objects.filter(agency__id=int(id_agency), role__name=GCHT)
		users = UserExtended.objects.all()
		for at in attributions:
			for u in users:
				if u.user.id == at.user.id:
					tab_guichetiers.append(u)
		serializer = UserExtendedSerializer(tab_guichetiers, many=True).data
		return Response(serializer, 200)

	@action(methods=["GET"], detail=False, url_name=r"guichetier", url_path=r"guichetier/(?P<phone>\d+)")
	def getGuichetier(self, request, phone):
		user = UserExtended.objects.get(telephone=int(phone))
		guichetiers = Attributions.objects.filter(role__name=GCHT)
		ext_u_tab = [x.user.id for x in guichetiers]
		if(not user.user.id in ext_u_tab):
			return Response({"status":"Non touvé !"},405)
		else:
			serializer = UserExtendedSerializer(user, many=False).data
			return Response(serializer, 200)


class AgencyViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Agency.objects.all()
	serializer_class = AgencySerializer

class DeliverViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Deliver.objects.all()
	serializer_class = DeliverSerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "first_name","last_name","phone"
	filterset_fields = {
		'phone': ['exact',]
	}

class RoleViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Role.objects.all()
	serializer_class = RoleSerializer

class AttributionsViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Attributions.objects.all()
	serializer_class = AttributionsSerializer

class MainStockViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = MainStock.objects.all()
	serializer_class = MainStockSerializer

class GuichetViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Guichet.objects.all()
	serializer_class = GuichetSerializer
	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "first_name","last_name","phone"
	filterset_fields = {
		'agency': ['exact',],
		'guichetier': ['exact',],
	}


class GuichetHistoriqueViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = HisoriqueGuichet.objects.all()
	serializer_class = HisoriqueGuichetSerializer


class StockAgencyViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = StockAgency.objects.all()
	serializer_class = StockAgencySerializer
	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "first_name","last_name","phone"
	filterset_fields = {
		'type_client': ['exact',],
	}

class ClientTypeViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = ClientType.objects.all()
	serializer_class = ClientTypeSerializer
	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "client_type","rate"
	filterset_fields = {
		'rate': ['exact',],
	}


class ClientViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Client.objects.all()
	serializer_class = ClientSerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "first_name","last_name","phone"
	filterset_fields = {
		'type_client': ['exact',]
	}

class TransfertViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Transfert.objects.all()
	serializer_class = TransfertSerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "amount",

	filterset_fields = {
		'user': ['exact',],
		'agency': ['exact',],
		'client': ['exact',]
	}


	@transaction.atomic()
	def createGuicheHistory(self, transfert):
		guichet:Guichet=Guichet.objects.get(guichetier=transfert.user, agency=transfert.agency)
		hist_guichet = HisoriqueGuichet(
			user=transfert.user,
			guichet=guichet,
			transfert=transfert,
			amount=transfert.amount,
			details=f"Trensfert de  {transfert.amount}\
						au guichet n°{guichet.name}\
						pour le client{transfert.client.first_name} {transfert.client.last_name}"
			)
		hist_guichet.save()
		return True


	@transaction.atomic()
	def create(self, request):
		data = request.data
		user = request.user
		stock_g:StockGuichetier=StockGuichetier.objects.get(user=request.user)
		agency:Agency=Agency.objects.get(id=int(data.get('agency')))
		amount=int(data.get('amount'))
		comission=0
		anypay=0

		client:Client=Client.objects.get(id=int(data.get('client')))

		if(data.get('comission')):
			comission = int(data.get('comission'))
			anypay = amount
		else:
			if(client.rate):
				anypay = amount+(amount*client.rate)
			else:
				anypay=amount+(amount*client.type_client.rate)

		if(anypay > stock_g.stock):
			return Response({'status':"Stock demandé indisponible !"},405)
		transfert = Transfert(
			user=request.user,
			agency=agency,
			paid_amount=amount,
			comission=comission,
			client=client
			)

		client.comissions+=comission

		transfert.amount = anypay
		stock_g.stock-=anypay
		stock_g.in_amount+=amount

		agency.cirulating_amount-=anypay

		main = AnyPay.objects.get(id=1)
		main.amount-=anypay

		main_stock=MainStock.instance()
		main_stock.total_amount-=anypay
		main_stock.circulating_amount-=anypay
		main_stock.save()

		transfert.save()
		hist = self.createGuicheHistory(transfert)
		if(not hist):
			return Response({'status':"Erreur survenue !"},405)
		agency.save()
		stock_g.save()
		main.save()
		client.save()
		serializer = TransfertSerializer(transfert, many=False).data
		return Response(serializer,201)

	def getAllTodayGuichetTransfert(self,agency):
		today_min_time = datetime.combine(timezone.now(),datetime.today().time().min)
		today_max_time = datetime.combine(timezone.now(),datetime.today().time().max)

		transferts = Transfert.objects\
		.filter(agency=agency, date__range=(today_min_time, today_max_time))

		return transferts

	@action(methods=["GET"], detail=False, url_name=r"today", url_path=r"today/(?P<agency_id>\d)")
	@transaction.atomic()
	def totalTodayAllGuichetTranfert(self, request, agency_id):
		agency:Agency=Agency.objects.get(id=int(agency_id))
		transferts = self.getAllTodayGuichetTransfert(agency)
		paid_amount = transferts.aggregate(Sum('paid_amount')).get('paid_amount__sum')
		transfered_amount = transferts.aggregate(Sum('amount')).get('amount__sum')
		return Response({
			"paid_amount":paid_amount if paid_amount!=None else 0,
			"transfered_amount":transfered_amount if transfered_amount !=None else 0
			},200)

class StockGuichetierViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = StockGuichetier.objects.all()
	serializer_class = StockGuichetierSerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "agency","user"
	filterset_fields = {
		'agency': ['exact',],
		'user':['exact',],
	}

	@action(methods=["POST"], detail=True, url_name=r"d-reception-g", url_path=r"d-reception-g")
	@transaction.atomic()
	def demandeReceptionG(self, request):
		stock=self.get_object()
		stock.reception=True
		stock.save()
		return Response(serializer,201)	

	@action(methods=["POST"], detail=False, url_name=r"reception-g", url_path=r"reception-g")
	@transaction.atomic()
	def receptionG(self, request):
		agency:Agency=Agency.objects.get(id=int(request.data.get('agency')))
		data = StockGuichetier.objects.filter(agency=agency, reception=False)
		serializer=StockGuichetierSerializer(data, many=True).data
		return Response(serializer,201)

	@action(methods=["POST"], detail=False, url_name=r"v-reception-g", url_path=r"v-reception-g")
	@transaction.atomic()
	def validerReceptionG(self, request):
		stock:StockGuichetier=StockGuichetier.objects.get(id=int(request.data.get('stock')))
		agency=stock.agency
		agency.in_amount+=stock.in_amount
		stock.in_amount=0
		stock.confirmed=False
		stock.save()
		agency.save()
		return Response(serializer,201)

	
class CommandeViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = Commande.objects.all()
	serializer_class = CommandeSerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "agency","confirmed"
	filterset_fields = {
		'agency': ['exact',],
		'confirmed':['exact',],
		'user':['exact',],
		'refused':['exact',]
	}

	@transaction.atomic()
	def checkQuotaMain(self, quantity):
		main_stock = MainStock.instance()
		if(quantity > main_stock.requested_amount+main_stock.available_amount):
			return False
		else:
			return True

	@transaction.atomic()
	def checkQuotaAgence(self, quantity, agency):
		agency:Agency = agency
		if(quantity > agency.available_amount+agency.requested_amount):
			return False
		else:
			return True

	@transaction.atomic()
	def createGuicheHistory(self, commande):
		guichet:Guichet=Guichet.objects.get(guichetier=commande.user, agency=commande.agency)
		hist_guichet = HisoriqueGuichet(
			user=commande.user,
			guichet=guichet,
			commande=commande,
			amount=commande.quantity,
			details=f"Commande de  {commande.quantity} au guichet n°{guichet.name}"
			)
		return True
		
	@transaction.atomic()
	def create(self, request):
		main_stock = MainStock.instance()
		data=request.data
		agency:Agency=Agency.objects.get(id=int(data.get('agency')))
		quantity=int(data.get('quantity'))
		commande = Commande(
			user=request.user,
			agency=agency,
			quantity=quantity,
			)
		if(checkUserAttribution(request.user)==DGA):
			if(not self.checkQuotaMain(quantity)):
				return Response(
					{"status":f"Stock indisponible!,veuillez entrer un montant inférieu ou égal à {main_stock.available_amount}!"}
					,405)
			main_stock.requested_amount+=quantity
			main_stock.available_amount-=quantity

		if(checkUserAttribution(request.user)==GCHT):
			if(not self.checkQuotaAgence(quantity,agency)):
				return Response(
					{"status":f"Stock indisponible!,veuillez entrer un montant inférieu ou égal à{agency.available_amount}!"}
					,405)
			else:
				if(self.createGuicheHistory(commande)):
					pass
				else:
					return Response(
						{"status":f"Erreur survenue !"},405)
				agency.requested_amount+=quantity
				agency.available_amount-=quantity
		agency.save()
		commande.save()
		main_stock.save()
		serializer = CommandeSerializer(commande, many=False).data
		return Response(serializer,201)

	def commandesDGA(self)->list:
		tab_dga = [x.user.id for x in Attributions.objects.filter(role__name=DGA)]
		commandes:list = Commande.objects.filter(user__id__in=tab_dga)
		return commandes

	@action(methods=["GET"], detail=False, url_name=r"commandes-unconfdga", url_path=r"commandes-unconfdga")
	@transaction.atomic()
	def commandesDGAUnconfirmed(self, request):
		if not request.user.is_superuser:
			return Response({"status":"Vous n'êtes pas habilité!"},405)
		commandes = [x for x in self.commandesDGA() if x.confirmed==False and x.refused==False]
		serializer=CommandeSerializer(commandes, many=True).data
		return Response(serializer, 200)

	@action(methods=["GET"], detail=False, url_name=r"commandes-confdga", url_path=r"commandes-confdga")
	@transaction.atomic()
	def commandesDGAConfirmed(self, request):
		if not request.user.is_superuser:
			return Response({"status":"Vous n'êtes pas habilité!"},405)
		commandes = [x for x in self.commandesDGA() if x.confirmed==True]
		serializer=CommandeSerializer(commandes, many=True).data
		return Response(serializer, 200)

	@action(methods=["GET"], detail=False, url_name=r"commandes-dga-refused", url_path=r"commandes-dga-refused")
	@transaction.atomic()
	def commandesDGARefused(self, request):
		if(not checkUserAttribution(request.user)==SU):
			return Response({"status":"Vous n'êtes pas habilité!"},405)
		commandes = [x for x in self.commandesDGA() if x.refused==True]
		serializer=CommandeSerializer(commandes, many=True).data
		return Response(serializer, 200)

	@action(methods=["GET"], detail=True, url_name=r"validate", url_path=r"validate")
	@transaction.atomic()
	def validate(self, request, pk):
		if(not checkUserAttribution(request.user)==SU):
			return Response({"status":"Non autorisé !"},405)
		else:
			main_stock=MainStock.instance()
			commande = self.get_object()
			if(not self.checkQuotaMain(commande.quantity)):
				return Response({"status":"Quantite indisponible !, veuillez importer AnyPay avant de continuer"},405)
			
			#calculating agency amount
			agency = commande.agency
			agency.available_amount += commande.quantity
			agency.total_amount = agency.requested_amount + agency.cirulating_amount+agency.available_amount

			commande.confirmed=True
			commande.refused=False
			commande.confirmed_user = request.user

			in_stock = StockAgency(
				agency=commande.agency,
				)
			in_stock.stock+=commande.quantity
			main_stock.circulating_amount+=commande.quantity
			main_stock.requested_amount-=commande.quantity
			main_stock.save()
			agency.save()
			in_stock.save()
			commande.save()
			return Response({"status":"Commande Validé avec success!"},200)

	@action(methods=["GET"], detail=True, url_name=r"validate-g", url_path=r"validate-g")
	@transaction.atomic()
	def validateCommGuichetier(self, request, pk):
		commande = self.get_object()
		agency=commande.agency

		if(checkUserAttribution(request.user)==GCHT):
			return Response(FORBIDEN_OPERATION_MSG, 405)
		if(not isDGAat(request.user, agency)):
			return Response(FORBIDEN_OPERATION_MSG, 405)

		if(not self.checkQuotaAgence(commande.quantity, agency)):
			return Response({"status":"Quantite indisponible !, veuillez passer une commande au DG de l'agence!"},405)
		in_stock:StockGuichetier = StockGuichetier.objects.get_or_create(user=commande.user,agency=commande.agency)
		in_stock=StockGuichetier.objects.get(user=commande.user,agency=commande.agency)
		in_stock.stock+=commande.quantity

		#agency calculating
		agency.requested_amount -= commande.quantity
		agency.cirulating_amount += commande.quantity
		agency.total_amount = agency.requested_amount + agency.cirulating_amount+agency.available_amount

		commande.confirmed=True
		commande.refused=False
		commande.confirmed_user=request.user

		agency.save()
		in_stock.save()
		commande.save()
		return Response({"status":"Commande Validé"},200)

	@action(methods=["GET"], detail=True, url_name=r"refused", url_path=r"refused")
	@transaction.atomic()
	def refused(self, request, pk):
		comm = self.get_object()
		main_stock = MainStock.instance()
		agency = comm.agency
		if(checkUserAttribution(comm.user)==DGA):
			if(not checkUserAttribution(request.user)==SU):
				return Response(FORBIDEN_OPERATION_MSG,405)
			else:
				main_stock.available_amount+=comm.quantity
				main_stock.requested_amount-=comm.quantity
		if(checkUserAttribution(comm.user)==GCHT):
			if(not isDGAat(request.user, comm.agency)):
				return Response(FORBIDEN_OPERATION_MSG,405)
			else:
				agency.requested_amount-=comm.quantity
				agency.available_amount+=comm.quantity
		hist=History(
		user=request.user,
		agency=agency,
		details=f"Refus de la commande n°{comm.id} par {request.user.first_name} {request.user.last_name}"
		)
		comm.refused=True
		comm.confirmed=False
		hist.save()
		main_stock.save()
		agency.save()
		comm.save()
		return Response({"status":"Opération éffectuée avec success!"},200)


	@transaction.atomic()
	def destroy(self,request,pk):
		comm=self.get_object()
		if(checkUserAttribution(comm.user)==DGA):
			if(not checkUserAttribution(request.user)==SU):
				return Response(FORBIDEN_OPERATION_MSG, 405)
		if(checkUserAttribution(comm.user)==GCHT):
			if(not isDGAat(request.user, comm.agency)):
				return Response(FORBIDEN_OPERATION_MSG,405)
		agency = comm.agency
		hist=History(
			user=request.user,
			agency=agency,
			details=f"Supperession de la commande n°{comm.id} par {request.user.first_name} {request.user.last_name}"
			)
		hist.save()
		agency.save()
		comm.delete()
		return Response({"status":"Commande supprimée avec success !"},200)

class HistoryViewSet(viewsets.ModelViewSet):
	authentication_classes = [JWTAuthentication, SessionAuthentication]
	permission_classes = [IsAuthenticated] 
	queryset = History.objects.all()
	serializer_class = HistorySerializer

	filter_backends = DjangoFilterBackend, SearchFilter
	search_fields = "agency","user"
	filterset_fields = {
		'agency': ['exact',],
		'user':['exact',],
	}