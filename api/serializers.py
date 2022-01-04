from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.validators import UnicodeUsernameValidator
from .models import *
from django.db import transaction
from rest_framework.response import Response
from django.contrib.auth.models import User

from api.serializers import *

class AnyPaySerializer(serializers.ModelSerializer):

	class Meta:
		model = AnyPay
		fields = "__all__"

class ImportationSerializer(serializers.ModelSerializer):

	class Meta:
		model = Importation
		fields = "__all__"

class ProvinceSerializer(serializers.ModelSerializer):

	class Meta:
		model = Province
		fields = "__all__"

class DeliverSerializer(serializers.ModelSerializer):

	class Meta:
		model = Deliver
		fields = "__all__"


class TokenPairSerializer(TokenObtainPairSerializer):

	def validate(self, attrs):
		data = super(TokenPairSerializer, self).validate(attrs)
		data['is_superuser'] = self.user.is_superuser
		data['id'] = self.user.id
		data['first_name'] = self.user.first_name
		data['last_name'] = self.user.last_name
		attributions = Attributions.objects.filter(user=self.user)
		data['attributions'] = AttributionsSerializer(attributions, many=True).data

		return data

class UserSerializer(serializers.ModelSerializer):
	password = serializers.CharField(write_only=True, allow_blank=True)
	
	class Meta:
		model = User
		read_only_fields = "is_active", "is_staff",
		exclude = "last_login","is_staff","date_joined","user_permissions","email"

		extra_kwargs = {
			'username': {
				'validators': [UnicodeUsernameValidator()],
			}
		}
class UserExtendedSerializer(serializers.ModelSerializer):
	user = UserSerializer()
	def to_representation(self, instance):
		representation=super(UserExtendedSerializer,self).to_representation(instance)
		representation['user'] = UserSerializer(instance.user, many=False).data
		attributions = Attributions.objects.get(user=instance.user)
		representation['attributions'] = AttributionsSerializer(attributions, many=False).data
		representation['telephone'] = instance.telephone
		try:
			guichet = Guichet.objects.get(guichetier=instance.user)
			print(guichet)
			representation['guichet'] = GuichetSerializer(guichet, many=False).data
		except Exception:
			pass
		return representation

	class Meta:
		model = UserExtended
		fields = "__all__"

class AgencySerializer(serializers.ModelSerializer):
	def to_representation(self, instance):
		representation =super().to_representation(instance)
		representation['province']=ProvinceSerializer(instance.province, many=False).data.get('name')
		return representation
	class Meta:
		model = Agency
		fields = "__all__"

class RoleSerializer(serializers.ModelSerializer):

	class Meta:
		model = Role
		fields = "__all__"
class AttributionsSerializer(serializers.ModelSerializer):
	def to_representation(self, instance):
		representation = super().to_representation(instance)
		representation['agency'] = AgencySerializer(instance.agency, many=False).data
		representation['role'] = RoleSerializer(instance.role, many=False).data
		return representation

	class Meta:
		model = Attributions
		fields = "__all__"
class StockAgencySerializer(serializers.ModelSerializer):

	class Meta:
		model = StockAgency
		fields = "__all__"

class GuichetSerializer(serializers.ModelSerializer):
	def to_representation(self, instance):
		representation = super().to_representation(instance)
		representation['agency'] = AgencySerializer(instance.agency, many=False).data
		representation['guichetier'] = UserSerializer(instance.guichetier, many=False).data
		return representation

	class Meta:
		model = Guichet
		fields = "__all__"

class HisoriqueGuichetSerializer(serializers.ModelSerializer):

	class Meta:
		model = HisoriqueGuichet
		fields = "__all__"

class ClientTypeSerializer(serializers.ModelSerializer):

	class Meta:
		model = ClientType
		fields = "__all__"
		
class MainStockSerializer(serializers.ModelSerializer):

	class Meta:
		model = MainStock
		fields = "__all__"
class ClientSerializer(serializers.ModelSerializer):
	def to_representation(self, instance):
		representation=super().to_representation(instance)
		representation['type_client']=ClientTypeSerializer(instance.type_client, many=False).data
		return representation

	class Meta:
		model = Client
		fields = "__all__"
class TransfertSerializer(serializers.ModelSerializer):

	def cleanUser(self,user):
		return {'id':user.id,"fullname":f"{user.first_name} {user.last_name}"}

	def cleanGuichet(self,guichet):
		return {'id':guichet.id,"name":guichet.name}

	def cleanAgency(self,agency):
		return {'id':agency.id,"name":agency.name}

	def cleanDeliver(self, deliver):
		return {'id':deliver.id, 'fullname':f"{deliver.first_name} {deliver.last_name}"}

	def to_representation(self, instance):
		representation=super(TransfertSerializer,self).to_representation(instance)
		representation['client']=ClientSerializer(instance.client, many=False).data
		representation['user']=self.cleanUser(instance.user)
		guichet = Guichet.objects.get(guichetier=instance.user)
		representation["guichet"] = self.cleanGuichet(guichet)
		representation['agency']=self.cleanAgency(instance.agency)
		if(instance.deliver):
			representation['deliver']=self.cleanDeliver(instance.deliver)
		return representation
		
	class Meta:
		model = Transfert
		fields = "__all__"

class StockGuichetierSerializer(serializers.ModelSerializer):
	def to_representation(self, instance):
		representation = super().to_representation(instance)
		representation['user'] = UserSerializer(instance.user, many=False).data
		return representation
	class Meta:
		model = StockGuichetier
		fields = "__all__"

class CommandeSerializer(serializers.ModelSerializer):
	def to_representation(self, instance):
		representation = super(CommandeSerializer,self).to_representation(instance)
		representation['agency'] = AgencySerializer(instance.agency, many=False).data
		attribution = Attributions.objects.get(user=instance.user)
		representation['attribution'] = AttributionsSerializer(attribution, many=False).data.get('role')
		representation['user'] = UserSerializer(instance.user, many=False).data
		return representation
	class Meta:
		model = Commande
		fields = "__all__"

class HistorySerializer(serializers.ModelSerializer):
	
	class Meta:
		model = History
		fields = "__all__"