from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('polling-unit/<int:pu_id>/', views.polling_unit_result, name='polling_unit_result'),
    path('lga-summed-result/', views.lga_summed_result, name='lga_summed_result'),
    path('get-lgas/', views.get_lgas, name='get_lgas'),
    path('get-wards/', views.get_wards, name='get_wards'),
    path('store-result/', views.store_polling_unit_result, name='store_polling_unit_result'),
]
