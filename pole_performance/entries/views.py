from django.shortcuts import render

"""
Enter Now link --> Entry form page

If not logged in: log in or register
If logged in but no disclaimer: disclaimer form link
If logged in and disclaimer but not already entered: Entry form
If already entered: Entry status (pending/accepted/unsuccessful)
Edit entry details?  edit bio, performance name, address, song choice
 Allow uploading file (songs)?

"""

def entries_home(request):

    return render(request, 'entries/home.html')
