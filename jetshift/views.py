from django.shortcuts import render


def home_view(request):
    return render(request, 'home.html', {
        'title': 'JetShift',
        'message': 'JetShift is Running!'
    })
