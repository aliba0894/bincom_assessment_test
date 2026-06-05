from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Sum, Max
from django.utils import timezone
from .models import PollingUnit, AnnouncedPuResults, Lga, Ward, Party, States


def polling_unit_result(request, pu_id):
    polling_unit = get_object_or_404(PollingUnit, uniqueid=pu_id)
    results = AnnouncedPuResults.objects.filter(
        polling_unit_uniqueid=str(pu_id)
    )

    lga = None
    ward = None
    try:
        lga = Lga.objects.get(lga_id=polling_unit.lga_id)
    except Lga.DoesNotExist:
        pass
    try:
        ward = Ward.objects.get(ward_id=polling_unit.ward_id, lga_id=polling_unit.lga_id)
    except Ward.DoesNotExist:
        pass

    context = {
        'polling_unit': polling_unit,
        'results': results,
        'lga': lga,
        'ward': ward,
    }
    return render(request, 'bincom_app/polling_unit_result.html', context)


def home(request):
    states = States.objects.all()
    lgas = None
    wards = None
    polling_units = PollingUnit.objects.none()

    state_id = request.GET.get('state_id')
    lga_id = request.GET.get('lga_id')
    ward_id = request.GET.get('ward_id')

    if ward_id:
        polling_units = PollingUnit.objects.filter(
            ward_id=ward_id, lga_id=lga_id
        ).order_by('polling_unit_name')
        lgas = Lga.objects.filter(state_id=state_id).order_by('lga_name')
        wards = Ward.objects.filter(lga_id=lga_id).order_by('ward_name')
    elif lga_id:
        wards = Ward.objects.filter(lga_id=lga_id).order_by('ward_name')
        polling_units = PollingUnit.objects.filter(
            lga_id=lga_id
        ).order_by('polling_unit_name')
        lgas = Lga.objects.filter(state_id=state_id).order_by('lga_name')
    elif state_id:
        lgas = Lga.objects.filter(state_id=state_id).order_by('lga_name')
        polling_units = PollingUnit.objects.filter(
            lga_id__in=Lga.objects.filter(state_id=state_id).values('lga_id')
        ).order_by('lga_id', 'polling_unit_name')

    return render(request, 'bincom_app/home.html', {
        'states': states,
        'lgas': lgas,
        'wards': wards,
        'polling_units': polling_units,
        'selected_state': state_id,
        'selected_lga': lga_id,
        'selected_ward': ward_id,
    })


def lga_summed_result(request):
    lgas = Lga.objects.filter(state_id=25).order_by('lga_name')
    summed_results = None
    selected_lga = None

    if request.GET.get('lga_id'):
        lga_id = request.GET['lga_id']
        selected_lga = get_object_or_404(Lga, lga_id=lga_id)
        pu_ids = PollingUnit.objects.filter(
            lga_id=lga_id
        ).values_list('uniqueid', flat=True)

        summed_results = AnnouncedPuResults.objects.filter(
            polling_unit_uniqueid__in=[str(pid) for pid in pu_ids]
        ).values('party_abbreviation').annotate(
            total_score=Sum('party_score')
        ).order_by('party_abbreviation')

    return render(request, 'bincom_app/lga_summed_result.html', {
        'lgas': lgas,
        'summed_results': summed_results,
        'selected_lga': selected_lga,
    })


def get_lgas(request):
    state_id = request.GET.get('state_id')
    lgas = Lga.objects.filter(state_id=state_id).values('lga_id', 'lga_name').order_by('lga_name')
    return JsonResponse(list(lgas), safe=False)


def get_wards(request):
    lga_id = request.GET.get('lga_id')
    wards = Ward.objects.filter(lga_id=lga_id).values('ward_id', 'ward_name').order_by('ward_name')
    return JsonResponse(list(wards), safe=False)


def store_polling_unit_result(request):
    lgas = Lga.objects.filter(state_id=25).order_by('lga_name')
    parties = Party.objects.all()

    if request.method == 'POST':
        lga_id = request.POST.get('lga_id')
        ward_id = request.POST.get('ward_id')
        polling_unit_name = request.POST.get('polling_unit_name', '')
        polling_unit_number = request.POST.get('polling_unit_number', '')

        max_id = PollingUnit.objects.aggregate(Max('uniqueid'))['uniqueid__max'] or 0
        new_pu_id = max_id + 1

        max_pu = PollingUnit.objects.filter(
            lga_id=lga_id, ward_id=ward_id
        ).aggregate(Max('polling_unit_id'))
        new_polling_unit_id = (max_pu['polling_unit_id__max'] or 0) + 1

        polling_unit = PollingUnit.objects.create(
            uniqueid=new_pu_id,
            polling_unit_id=new_polling_unit_id,
            ward_id=ward_id,
            lga_id=lga_id,
            polling_unit_name=polling_unit_name,
            polling_unit_number=polling_unit_number,
            entered_by_user='admin',
            date_entered=timezone.now(),
            user_ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        for party in parties:
            score = request.POST.get(f'score_{party.partyid}', '0')
            if score and int(score) > 0:
                AnnouncedPuResults.objects.create(
                    polling_unit_uniqueid=str(new_pu_id),
                    party_abbreviation=party.partyid,
                    party_score=int(score),
                    entered_by_user='admin',
                    date_entered=timezone.now(),
                    user_ip_address=request.META.get('REMOTE_ADDR', ''),
                )

        return redirect('polling_unit_result', pu_id=new_pu_id)

    return render(request, 'bincom_app/store_polling_unit_result.html', {
        'lgas': lgas,
        'parties': parties,
    })
