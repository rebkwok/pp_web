from django.shortcuts import render


def home(request):
    return render(request, 'web/home2020.html')

