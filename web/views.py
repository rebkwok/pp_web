from django.shortcuts import render


def home(request):
    return render(request, 'web/home2020_placeholder.html')


def home2018(request):
    return render(request, 'web/home2018.html')


def home2020(request):
    return render(request, 'web/home2020.html')

