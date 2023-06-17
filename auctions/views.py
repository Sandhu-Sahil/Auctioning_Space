from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django import forms

from .models import User, Auction, Bid, Category, Comment, Watchlist, Person

class AuctionForm(forms.ModelForm):
    """Form for the image model"""
    class Meta:
        model = Auction
        fields = ('title', 'description', 'starting_bid', 'category', 'person', 'image')
        #widgets = {#'category' : forms.Select(choices=Category.objects.all(), attrs={'class' : 'form-control'}),
                   #'person' : forms.Select(choices=Person.objects.all(), attrs={'class' : 'form-control'}),
                   #'title': forms.TextInput(attrs={'class': 'form-control'}),
                   #'description': forms.TextInput(attrs={'class': 'form-control'}),
                   #'starting_bid': forms.NumberInput(attrs={'class': 'form-control'})
                   #} 


def index(request):
    auctions = Auction.objects.all().order_by('id').reverse()
    persons = Category.objects.all()
    user = request.user 
    if user.id is None:
        context = {
            'auctions': auctions,
            'persons': persons,
        }
        return render(request, "auctions/index.html", context)
    my_watchlist = Watchlist.objects.get(user=request.user)
    
    context = {
        'auctions': auctions,
        'my_watchlist': my_watchlist,
        'persons': persons,
    }
    return render(request, "auctions/index.html", context)


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "auctions/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        if request.user.is_authenticated:
            return redirect('index')
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        watchlist = Watchlist.objects.create(user = request.user)
        watchlist.save()
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")


@login_required
def add_auction(request):
    persons = Category.objects.all()
    user = request.user
    if user.id is None:
        return redirect('login')
    my_watchlist = Watchlist.objects.get(user=request.user)
    
    if request.method == 'GET':
        context = {
            'form': AuctionForm(),
            'persons': persons,
        }

        return render(request, "auctions/add_auctions.html", context)
    else:
        form = AuctionForm(request.POST, request.FILES)

        if form.is_valid():
            title = form.cleaned_data['title']
            description = form.cleaned_data['description']
            starting_bid = form.cleaned_data['starting_bid']
            category = form.cleaned_data['category']
            person = form.cleaned_data['person']
            image = form.cleaned_data['image']

            auctionCreated = Auction.objects.create(
                user=request.user,
                title=title, 
                description=description, 
                starting_bid=starting_bid,
                category=category,
                person=person,
                image=image,
            )
            
            return redirect('index')


def category_view(request, category, person):
    user = request.user
    # if user.id is None:
    #     return redirect('login')
    
    category_name = Category.objects.get(name=category)
    person_name = Person.objects.get(person=person)
    auctions = Auction.objects.filter(category=category_name, person=person_name).order_by('id').reverse()
    persons = Category.objects.all()
    print(user)
    print(user.id)
    
    context = {
        'auctions': auctions,
        'category_name': category_name,
        'persons': persons,
    }
    return render(request, "auctions/category.html", context)


@login_required
def my_listings(request, user):
    user_object = User.objects.get(username=user)
    auctions = Auction.objects.filter(user=user_object)
    my_watchlist = Watchlist.objects.get(user=request.user)
    persons = Category.objects.all()
    if request.user.username != user:
        return redirect('my_listings', user=request.user.username)

    context = {
        'auctions': auctions,
        'my_watchlist': my_watchlist,
        'persons': persons,
    }

    return render(request, "auctions/my_listings.html", context)


@login_required
def watchlist(request):
    persons = Category.objects.all()
    if request.user.id is None:
        return redirect('index')

    my_watchlist = Watchlist.objects.get(user=request.user)
    print(my_watchlist.auctions)
    context = {
        'my_watchlist': my_watchlist,
        'persons': persons,
    }
    return render(request, "auctions/watchlist.html", context)


@login_required
def add_to_watchlist(request, auction):

    auction_to_add = Auction.objects.get(id=auction)
    watchlist = Watchlist.objects.get(user=request.user)
    print(watchlist)
    if auction_to_add not in watchlist.auctions.all():
        watchlist.auctions.add(auction_to_add)
        watchlist.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))



@login_required
def bid_to_auction(request, auction):
 
    auction_to_add = Auction.objects.get(id=auction)
    total_bid = request.GET["totalBid"]
    bid = Bid.objects.create(user=request.user, auction=auction_to_add, bid=total_bid)
    auction_to_add.bids.add(bid)
    if auction_to_add.last_bid:
        if int(auction_to_add.last_bid.bid) < int(bid.bid):
            auction_to_add.last_bid = bid
    else:
        auction_to_add.last_bid = bid
    auction_to_add.save()

    persons = Category.objects.all()
    my_watchlist = Watchlist.objects.get(user=request.user)
    auction = Auction.objects.get(id=auction)
    comments = auction.comments.all().order_by('id').reverse()
    context = {
        'auction': auction,
        'my_watchlist': my_watchlist,
        'persons': persons,
        'comments': comments,
    }
    return render(request, 'auctions/auction_view.html', context)


@login_required
def auction_view(request, auction):
    if request.method == 'GET':
        persons = Category.objects.all()
        if request.user.id is None:
            return redirect('login')

        my_watchlist = Watchlist.objects.get(user=request.user)
        print(my_watchlist.auctions)
        auction = Auction.objects.get(id=auction)
        comments = auction.comments.all().order_by('id').reverse()
        context = {
            'auction': auction,
            'my_watchlist': my_watchlist,
            'persons': persons,
            'comments': comments,
        }
        return render(request, 'auctions/auction_view.html', context)


@login_required
def add_comment(request, auction):
    if request.method == 'POST':
        auction = Auction.objects.get(id=auction)
        comment = request.POST['comment']
        if not comment:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        comment_object = Comment.objects.create(comment=comment, user=request.user)
        auction.comments.add(comment_object)
        auction.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def delete_comment(request, comment):
    comment_object = Comment.objects.get(id=comment)
    comment_object.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


@login_required
def delete_auction_from_watchlist(request, auction):
    auction = Auction.objects.get(id=auction)
    my_watchlist = Watchlist.objects.get(user=request.user)
    my_watchlist.auctions.remove(auction)
    my_watchlist.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    


@login_required
def delete_auction(request, auction):
    if request.method == 'GET':
        auction = Auction.objects.get(id=auction)
        if auction.user == request.user:
            auction.delete()
            return redirect('index')


@login_required
def close_listing(request, auction):
    if request.method == 'GET':
        auction_object = Auction.objects.get(id=auction)
        auction_object.closed = True
        auction_object.save()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))