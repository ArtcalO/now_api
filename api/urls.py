from django.urls import path, include
from rest_framework import routers
from .views import *
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

router = routers.DefaultRouter()

router.register("user", UserViewset)
router.register("anypay", AnyPayViewSet)
router.register("main-stock", MainStockViewSet)
router.register("agency", AgencyViewSet)
router.register("account", UserExtendedViewSet)
router.register("role", RoleViewSet)
router.register("commande", CommandeViewSet)
router.register("in-stock-agence", StockAgencyViewSet)
router.register("attribution", AttributionsViewSet)
router.register("client", ClientViewSet)
router.register("client-type", ClientTypeViewSet)
router.register("stock-guichetier", StockGuichetierViewSet)
router.register("tranfert", TransfertViewSet)
router.register("province", ProvinceViewSet)
router.register("guichet", GuichetViewSet)
router.register("hist-guichet", GuichetHistoriqueViewSet)
router.register("history", HistoryViewSet)
router.register("importation", ImportationViewSet)
router.register("livreur", DeliverViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('login/', TokenPairView.as_view()),
    path('refresh/', TokenRefreshView.as_view()),
    path('api-auth/', include('rest_framework.urls')),
]
