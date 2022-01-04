from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import date, datetime
from typing import List


class AnyPay(models.Model):
	id=models.AutoField(primary_key=True)
	amount = models.PositiveIntegerField()

	def __str__(self):
		return str(self.amount)

class Importation(models.Model):
	id=models.BigAutoField(primary_key=True)
	user=models.ForeignKey(User, related_name="importation_user", on_delete=models.CASCADE)
	amount = models.PositiveIntegerField()
	date=models.DateTimeField(auto_now_add=True)

class MainStock(models.Model):
	id = models.AutoField(primary_key=True)
	total_amount = models.PositiveIntegerField(default=0)
	requested_amount = models.PositiveIntegerField(default=0)
	circulating_amount = models.PositiveIntegerField(default=0)
	available_amount = models.PositiveIntegerField(default=0)
	last_modified = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.total_amount}"

	@staticmethod
	def instance():
		return  MainStock.objects.get_or_create(id=1)[0]


class Reception(models.Model):
	id=models.BigAutoField(primary_key=True)
	amount = models.PositiveIntegerField()
	user = models.ForeignKey(User, related_name="reception_user", on_delete=models.CASCADE)
	_from = models.ForeignKey(User, related_name='reception_from', on_delete=models.CASCADE)
	is_valid = models.BooleanField(default=False)
	date = models.DateTimeField(auto_now=True)

	def __str__(self):
		return str(self.amount)

class Deliver(models.Model):
	id=models.BigAutoField(primary_key=True)
	first_name = models.CharField(max_length=100)
	last_name= models.CharField(max_length=100)
	phone = models.CharField(max_length=100, unique=True)
	comissions = models.FloatField(default=0)
	date = models.DateTimeField(auto_now=True)

	def __str__(self):
		return self.first_name+" "+self.last_name

class UserExtended(models.Model):
	id=models.BigAutoField(primary_key=True)
	user = models.ForeignKey(User,related_name="userextended_user",on_delete=models.CASCADE)
	telephone = models.CharField(max_length=50)

	def __str__(self):
		return self.user.username

class Province(models.Model):
	id=models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	def __str__(self):
		return self.name

class Agency(models.Model):
	id = models.AutoField(primary_key=True)
	name = models.CharField(max_length=100)
	province = models.ForeignKey(Province, related_name="agency_province", on_delete=models.CASCADE)
	location = models.CharField(max_length=200, null=True, blank=True)
	total_amount = models.FloatField(default=0)
	requested_amount = models.FloatField(default=0)
	cirulating_amount = models.FloatField(default=0)
	available_amount = models.FloatField(default=0)
	cash_amount = models.FloatField(default=0)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.name}"

class Role(models.Model):
	id=models.AutoField(primary_key=True)
	name = models.CharField(max_length=50)

	def __str__(self):
		return f"{self.name}"

class Attributions(models.Model):
	id=models.AutoField(primary_key=True)
	user = models.ForeignKey(User,related_name='attribution_user',on_delete=models.CASCADE)
	role = models.ForeignKey(Role, related_name="attribution_role", on_delete=models.CASCADE)
	agency = models.ForeignKey(Agency, related_name="attribution_agency", on_delete=models.CASCADE, null=True,blank=True)

	def __str__(self):
		return f"{self.user}-{self.role.name}-{self.agency.name if self.agency else None}"

class StockAgency(models.Model):
	id=models.BigAutoField(primary_key=True)
	agency = models.ForeignKey(Agency, related_name="stockagency_agency", on_delete=models.CASCADE)
	stock = models.PositiveIntegerField(default=0)
	date = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.agency.name}-{self.stock}"

class Guichet(models.Model):
	id=models.BigAutoField(primary_key=True)
	name = models.CharField(max_length=20)
	agency = models.ForeignKey(Agency, related_name="guichet_agency", on_delete=models.CASCADE)
	guichetier = models.ForeignKey(User, related_name="guichet_guichetier", on_delete=models.CASCADE, null=True, blank=True)
	date=models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.name

class StockGuichetier(models.Model):
	id=models.BigAutoField(primary_key=True)
	user=models.ForeignKey(User, related_name="stockguichetier_user", on_delete=models.CASCADE)
	agency = models.ForeignKey(Agency, related_name="stockguichetier_agency", on_delete=models.CASCADE)
	stock = models.PositiveIntegerField(default=0)
	in_amount = models.FloatField(default=0)
	reception = models.BooleanField(default=False) 
	date = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.agency.name}-{self.stock}"

class Commande(models.Model):
	id=models.BigAutoField(primary_key=True)
	user = models.ForeignKey(User, related_name="commandeagence_user", on_delete=models.CASCADE)
	agency = models.ForeignKey(Agency, related_name="commandeagence_agency", on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=0)
	details = models.CharField(max_length=50, null=True, blank=True)
	confirmed = models.BooleanField(default=False)
	refused = models.BooleanField(default=False)
	confirmed_user = models.ForeignKey(User,null=True,blank=True,related_name="commande_confirmeduser", on_delete=models.CASCADE)
	confirmed_date = models.DateTimeField(auto_now=True)
	date = models.DateTimeField(auto_now_add=True)
	def __str__(self):
		return f"{self.user.username}-{self.quantity}-{self.agency.name}"

class ClientType(models.Model):
	id=models.AutoField(primary_key=True)
	client_type = models.CharField(max_length=50)
	rate = models.FloatField(default=0)
	
	def __str__(self):
		return f"{self.client_type}- taux : {self.rate}"


class Client(models.Model):
	id = models.AutoField(primary_key=True)
	first_name = models.CharField(max_length=100)
	last_name= models.CharField(max_length=100)
	phone = models.CharField(max_length=100, unique=True)
	type_client = models.ForeignKey(ClientType,on_delete=models.CASCADE)
	comissions = models.FloatField(default=0)
	rate = models.FloatField(default=0, null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True, editable=False)

	def __str__(self):
		return f"{self.first_name} {self.last_name}"


class Transfert(models.Model):
	id = models.BigAutoField(primary_key=True)
	user = models.ForeignKey(User, related_name="transfert_user", on_delete=models.CASCADE,null=True, blank=True)
	agency = models.ForeignKey(Agency, related_name="transfert_agency", on_delete=models.CASCADE, null=True)
	amount = models.PositiveIntegerField(default=0)
	paid_amount = models.FloatField(default=0, editable=False)
	client = models.ForeignKey(Client, related_name="transfert_client", on_delete=models.CASCADE)
	deliver = models.ForeignKey(Deliver, related_name="transfert_deliver", on_delete=models.CASCADE, null=True,blank=True)
	comission = models.PositiveIntegerField(default=0, null=True, blank=True)
	date = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"{self.user.username}-{self.amount}"

class HisoriqueGuichet(models.Model):
	id=models.BigAutoField(primary_key=True)
	user = models.ForeignKey(User, related_name="historique_user", on_delete=models.CASCADE, null=True, blank=True)
	guichet = models.ForeignKey(Guichet, related_name="historique_guichet", on_delete=models.CASCADE, null=True, blank=True)
	commande = models.ForeignKey(Commande, related_name="historique_commande", on_delete=models.CASCADE, null=True,blank=True)
	transfert = models.ForeignKey(Transfert, related_name="historique_transfert", on_delete=models.CASCADE, null=True, blank=True)
	details = models.TextField()
	amount = models.FloatField(default=0)
	date = models.DateTimeField(auto_now=True)


class History(models.Model):
	id=models.BigAutoField(primary_key=True)
	user = models.ForeignKey(User, related_name="history_user", on_delete=models.CASCADE)
	agency = models.ForeignKey(Agency, related_name="history_agency", on_delete=models.CASCADE, null=True, blank=True)
	details = models.TextField()
	date= models.DateTimeField(auto_now=True)