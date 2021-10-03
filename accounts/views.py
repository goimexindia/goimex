import urllib

import secret as secret
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.db.models import Q
from django.http import FileResponse, HttpResponseBadRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User, auth
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views import View
from django.views.generic import CreateView
import os
from django.conf import settings
from gitdb.utils.encoding import force_text

from blog.models import Post
from buyerseller.models import Rfq, Customer, Order, Product, Category, Admin, ProdComment
from goimex.token import account_activation_token
from templates.my_captcha import FormWithCaptcha
from .forms import *
from django.contrib.auth.decorators import login_required

from .models import Profile, Contactme, Subscriber, Whatyouwant
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
import razorpay

import json
from django.views.decorators.csrf import csrf_exempt

from verify_email.email_handler import send_verification_email
from django.utils.encoding import force_bytes

from django.shortcuts import render
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest


def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            messages.info(request, "Logged IN successfully!")
            auth.login(request, user)
            return redirect("/")
        else:
            messages.info(request, 'Invalid Credentials')
            return redirect('login')
    else:
        return render(request, 'login.html')


class ActivateAccount(View):
    def get(self, request, uidb64, token, *args, **kwargs):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.profile.email_confirmed = True
            user.save()
            login(request, user)
            messages.success(request, 'Your account have been confirmed.')
            return redirect('home')
        else:
            messages.warning(request, 'The confirmation link was invalid, possibly because it has already been used.')
            return redirect('home')


class AdminRequiredMixin(object):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and Admin.objects.filter(user=request.user).exists():
            pass
        else:
            return redirect("/admin-login/")
        return super().dispatch(request, *args, **kwargs)


def update_user_data(user):
    Profile.objects.update_or_create(user=user, defaults={'mob': user.profile.mobile})
    Customer.objects.update_or_create(user=user, defaults={'username': user.customer.full_name})


def register1(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        get_recaptcha = request.POST.get("g-recaptcha-response")
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Your account has been created! You are now able to log in')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form, "captcha": FormWithCaptcha,
                                             'recaptcha_site_key': settings.GOOGLE_RECAPTCHA_SITE_KEY}, )


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        get_recaptcha = request.POST.get("g-recaptcha-response")
        if form.is_valid():
            email = request.POST['email']
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            current_site = get_current_site(request)
            message = render_to_string('accounts/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            mail_subject = 'Activate your GOIMEX account.'
            to_email = form.cleaned_data.get('email')
            to_list = [email, settings.EMAIL_HOST_USER]
            from_email = settings.EMAIL_HOST_USER
            send_mail(mail_subject, message, from_email, to_list, fail_silently=True)
            return HttpResponse('Please confirm your email address to complete the registration')
    else:
        form = UserRegisterForm()

    return render(request, 'register.html', {'form': form})


def logout(request):
    auth.logout(request)
    messages.info(request, "Logged OUT successfully!")
    return redirect('/')


@login_required
def adminprofile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your profile data has been updatedd!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    order = Post.objects.filter(author=request.user).order_by('-date_posted')
    paginator = Paginator(order, 6)
    page_number = request.GET.get('page')
    order_list = paginator.get_page(page_number)
    order = order_list
    rfq = Rfq.objects.filter(author=request.user).order_by('-created_on')
    paginator = Paginator(rfq, 6)
    page_number = request.GET.get('page')
    rfq_list = paginator.get_page(page_number)
    rfq = rfq_list

    product = Product.objects.filter(author=request.user).order_by('-created_on')
    paginator = Paginator(product, 6)
    page_number = request.GET.get('page')
    product_list = paginator.get_page(page_number)
    product = product_list

    myorders = Order.objects.filter(cart__customer=request.user.customer).order_by("-id")
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'orders': order,
        'rfq': rfq,
        'myorders': myorders,
        'product': product,
    }
    return render(request, 'accounts/adminprofile.html', context)


@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your profile data has been updatedd!')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    order = Post.objects.filter(author=request.user).order_by('-date_posted')
    paginator = Paginator(order, 6)
    page_number = request.GET.get('page')
    order_list = paginator.get_page(page_number)
    order = order_list
    rfq = Rfq.objects.filter(author=request.user).order_by('-created_on')
    paginator = Paginator(rfq, 6)
    page_number = request.GET.get('page')
    rfq_list = paginator.get_page(page_number)
    rfq = rfq_list

    product = Product.objects.filter(author=request.user).order_by('-created_on')
    paginator = Paginator(product, 6)
    page_number = request.GET.get('page')
    product_list = paginator.get_page(page_number)
    product = product_list

    myorders = Order.objects.filter(cart__customer=request.user.customer).order_by("-id")
    ppostcount = Post.objects.filter(author=request.user).count()
    pproductcount = Product.objects.filter(author=request.user).count()
    pordercount = Order.objects.filter(customer=request.user.customer).count()
    pinquirycount = ProdComment.objects.filter(product__author=request.user).count()
    context = {
        'u_form': u_form,
        'p_form': p_form,
        'orders': order,
        'rfq': rfq,
        'myorders': myorders,
        'product': product,
        'ppostcount': ppostcount,
        'pordercount': pordercount,
        'pproductcount': pproductcount,
        'pinquirycount': pinquirycount,
    }
    return render(request, 'profile.html', context)


@login_required
def myorganization(request):
    if request.method == 'POST':
        p_form = BussinessUpdateForm(request.POST,
                                     request.FILES,
                                     instance=request.user.profile)
        u_form = CompanyImageForm(request.POST,
                                  request.FILES,
                                  instance=request.user.profile)
        if u_form.is_valid() and u_form.is_valid():
            p_form.save()
            u_form.save()
            messages.success(request, f'Your profile data has been updatedd!')
            return redirect('profile')
    else:
        p_form = BussinessUpdateForm(instance=request.user.profile)
        u_form = CompanyImageForm(instance=request.user.profile)
    profile = Profile.objects.filter(user=request.user).order_by('-id')

    context = {
        'p_form': p_form,
        'u_form': u_form,
        'profile': profile,
    }
    return render(request, 'accounts/mybussiness.html', context)


@login_required
def myorder(request):
    order = Post.objects.filter(author=request.user).order_by('-date_posted')
    paginator = Paginator(order, 6)
    page_number = request.GET.get('page')
    order_list = paginator.get_page(page_number)
    order = order_list
    myorders = Order.objects.filter(cart__customer=request.user.customer).order_by("-id")
    context = {
        'orders': order,
        'myorders': myorders,
    }
    return render(request, 'accounts/myorders.html', context)


@login_required
def catalog(request):
    product = Product.objects.filter(author=request.user).order_by('-created_on')
    paginator = Paginator(product, 6)
    page_number = request.GET.get('page')
    product_list = paginator.get_page(page_number)
    product = product_list
    context = {
        'product': product,
    }
    return render(request, 'accounts/catalog.html', context)


def membership(request):
    return render(request, 'accounts/membership.html')


def myrfq(request):
    rfq = Rfq.objects.filter(author=request.user).order_by('-created_on')
    context = {
        'rfq': rfq,
    }
    return render(request, 'accounts/myrfq.html', context)


def mypost(request):
    ppost = Post.objects.filter(author=request.user).order_by('-created_on')
    ppostcount = Post.objects.filter(author=request.user).count()
    paginator = Paginator(ppost, 6)
    page_number = request.GET.get('page')
    post_list = paginator.get_page(page_number)
    context = {
        'post': post_list,
        'count': ppostcount,
    }
    return render(request, 'accounts/mypost.html', context)


def dashboard(request):
    context = {}
    return render(request, 'dashboard.html', context)


def transactions(request):
    context = {}
    return render(request, 'transactions.html', context)


def safedeal(request):
    context = {}
    return render(request, 'safedeal.html', context)


def policy(request):
    context = {}
    return render(request, 'accounts/privacypolicy.html', context)


def terms(request):
    context = {}
    return render(request, 'accounts/terms.html', context)


def faq1(request):
    filename = "faq.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, "goimex", filename)
    print(filepath)
    return FileResponse(open(filepath, 'rb'), content_type='application/pdf')


def faq(request):
    context = {}
    return render(request, 'accounts/snippets/faq.html', context)


def success(request):
    context = {}
    return render(request, 'buyerseller/rfqsuccess.html', context)


def listing(request):
    context = {}
    return render(request, 'accounts/listingpolicy.html', context)


def buyerjoining(request):
    context = {}
    return render(request, 'accounts/buyerjoining.html', context)


class CategoryCreateView(LoginRequiredMixin, CreateView):
    template_name = "accounts/category.html"
    form_class = CategoryForm
    success_url = reverse_lazy("admincategorylist")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class AdminCategoryListView(AdminRequiredMixin, ListView):
    template_name = "accounts/admincategorylist.html"
    queryset = Category.objects.all().order_by("-id")
    context_object_name = "allcat"

    def get_context_data(self, **kwargs):
        context = super(AdminCategoryListView, self).get_context_data(**kwargs)
        allcat = Category.objects.all().order_by("-id")
        paginator = Paginator(allcat, 5)
        page_number = self.request.GET.get('page')
        cat_list = paginator.get_page(page_number)
        context['allcat'] = cat_list
        return context


def whatyouwant(request):
    if request.method == "POST":
        product_want = request.POST['products_want']
        full_name = request.POST['full_name']
        email = request.POST['email']
        company_name = request.POST['company_name']
        username = request.user.username
        contact_input_email = request.POST['email']
        phone_number = request.POST['phone_number']
        type = request.POST['type']

        subject = "Your Requirement needs "
        from_email = settings.EMAIL_HOST_USER
        contact_input_email = request.POST['email']
        to_list = [contact_input_email, settings.EMAIL_HOST_USER]
        message = "Dear " + full_name + ",\n\n" \
                  + "Thank you for your request on 'TELL US WHAT YOU NEED" + "\n\n\n" \
                  + "We will get in touch with you soon." + "\n\n\n" \
                  + "Your message details : -" + "\n\n\n" \
                  + "Message From-" + full_name + "\n" \
                  + "Email:-" + contact_input_email + "\n\n" \
                  + "Mobile:-" + phone_number + "\n\n" \
                  + "Subject-" + product_want + "\n\n" \
                  + "Warm Regards \n\n From: Goimex Support Team"
        send_mail(subject, message, from_email, to_list, fail_silently=True)
        whatyouwant = Whatyouwant(email=contact_input_email, product_want=product_want,
                                  full_name=full_name, type=type, phone_number=phone_number,
                                  company_name=company_name)
        whatyouwant.save()
        context = {
        }
        return render(request, "whatyouwant.html", context)


def subscriber(request):
    if request.method == "POST":
        user = request.user.id
        username = request.user.username
        contact_input_email = request.POST['email']
        subject = " Newsletter "
        from_email = settings.EMAIL_HOST_USER
        contact_input_email = request.POST['email']
        to_list = [contact_input_email, settings.EMAIL_HOST_USER]
        message = "Dear " + username + ",\n\n" \
                  + "Thank you for signing up for my email newsletter!" + "\n\n\n" \
                  + "We will get in touch with you soon." + "\n\n\n" \
                  + "-" + "\n" \
                  + "Warm Regards \n\n From: Goimex Support Team"
        send_mail(subject, message, from_email, to_list, fail_silently=False)
        subscriber = Subscriber(email=contact_input_email)
        subscriber.save()
        context = {
        }
        return render(request, "subscriber.html", context)


@login_required(login_url='login')
def contact(request):
    if request.method == "POST":
        input_name = request.POST['input_name']
        contact_input_email = request.POST['contact_input_email']
        contact_input_subject = request.POST['contact_input_subject']
        contact_input_mobile = request.POST['contact_input_mobile']
        contact_input = request.POST['contact_input']
        mobile = request.POST['contact_input_mobile']
        subject = "Thank you for contacting Goimex.com."
        message = "Dear " + input_name + ",\n\n" \
                  + "We will get in touch with you soon." + "\n\n\n" \
                  + "Your message details : -" + "\n" \
                  + "Message From-" + input_name + "\n" \
                  + "Email:-" + contact_input_email + "\n\n" \
                  + "Mobile:-" + mobile + "\n\n" \
                  + "Subject-" + contact_input_subject + "\n\n" \
                  + "Details-" + contact_input + "\n\n\n" \
                  + "Warm Regards \n\n From: Goimex Support Team"
        from_email = settings.EMAIL_HOST_USER
        to_list = [contact_input_email, settings.EMAIL_HOST_USER]
        send_mail(subject, message, from_email, to_list, fail_silently=True)

        name = request.POST['input_name']
        email = request.POST['contact_input_email']
        subject = request.POST['contact_input_subject']
        message = request.POST['contact_input']
        contactme = Contactme(name=name, email=email, mobile=mobile, subject=subject, message=message)
        contactme.save()
        dest = Contactme.objects.filter(name=name, email=email, mobile=mobile, message=message).order_by('-id')[:1]

        context = {
            'contact_input_name': input_name,
            'dest': dest,
            'header': 'Contact',

        }
        return render(request, 'contact.html', context)
    else:
        context = {
        }
        return render(request, "contact.html", context)


@login_required(login_url='login')
def basicpayment(request):
    keyid = 'rzp_live_Ov8XlxQ15IJQBh'
    keySecret = 'Ke4e8CHQOTIf3CUGLwbwhj0P'
    coldcoffe_data = {
        'name': request.user.username,
        'amount': int("9999") * 1,
    }
    form = CoffeePaymentForm()
    if request.method == "POST":
        name = request.POST.get('name')
        amount = int("999900") * 1
        order_receipt = 'order_rcptid_11'
        notes = {'BASIC'}
        client = razorpay.Client(auth=(keyid, keySecret))
        response_payment = client.order.create(dict(amount=amount, currency='INR'))
        order_id = response_payment['id']
        order_status = response_payment['status']
        if order_status == 'created':
            cold_coffee = ColdCoffe(
                name=name,
                amount=amount,
                order_id=order_id
            )
            cold_coffee.save()
            response_payment['name'] = name

            form = CoffeePaymentForm(request.POST or None)
            return render(request, 'accounts/payment.html', {'form': form, 'payment': response_payment})

    form = CoffeePaymentForm(initial=coldcoffe_data)
    return render(request, 'accounts/payment.html', {'form': form})


@csrf_exempt
def success(request):
    return render(request, "accounts/success.html")


def silverpayment(request):
    keyid = 'rzp_live_Ov8XlxQ15IJQBh'
    keySecret = 'Ke4e8CHQOTIf3CUGLwbwhj0P'
    coldcoffe_data = {
        'name': request.user.username,
        'amount': int("18999") * 1,
    }
    form = CoffeePaymentForm()

    if request.method == "POST":
        name = request.POST.get('name')
        amount = 1899900
        client = razorpay.Client(
            auth=(keyid, keySecret))
        payment = client.order.create(dict(amount=amount, currency='INR'))
        response_payment = client.order.create(dict(amount=amount, currency='INR'))
        order_id = response_payment['id']
        order_status = response_payment['status']
        if order_status == 'created':
            cold_coffee = ColdCoffe(
                name=name,
                amount=amount,
                order_id=order_id,
            )
            cold_coffee.save()
            response_payment['name'] = name
            form = CoffeePaymentForm(request.POST or None)
            return render(request, 'accounts/payment1.html', {'form': form, 'payment': payment})
    form = CoffeePaymentForm(initial=coldcoffe_data)
    return render(request, 'accounts/payment1.html', {'form': form})


def goldpayment(request):
    keyid = 'rzp_live_Ov8XlxQ15IJQBh'
    keySecret = 'Ke4e8CHQOTIf3CUGLwbwhj0P'
    coldcoffe_data = {
        'name': request.user.username,
        'amount': int("36999") * 1,
    }
    form = CoffeePaymentForm()
    if request.method == "POST":
        name = request.POST.get('name')
        amount = 3699900
        client = razorpay.Client(
            auth=(keyid, keySecret))
        response_payment = client.order.create(dict(amount=amount, currency='INR'))
        order_id = response_payment['id']
        order_status = response_payment['status']
        if order_status == 'created':
            cold_coffee = ColdCoffe(
                name=name,
                amount=amount,
                order_id=order_id,
            )
            cold_coffee.save()
            response_payment['name'] = name
            form = CoffeePaymentForm(request.POST or None)
            return render(request, 'accounts/payment2.html', {'form': form, 'payment': response_payment})
    form = CoffeePaymentForm(initial=coldcoffe_data)
    return render(request, 'accounts/payment2.html', {'form': form})


def payment_status(request):
    response = request.POST
    keyid = 'rzp_live_Ov8XlxQ15IJQBh'
    keySecret = 'Ke4e8CHQOTIf3CUGLwbwhj0P'
    params_dict = {
        'razorpay_order_id': response['razorpay_order_id'],
        'razorpay_payment_id': response['razor_payment_id'],
        'razor_signature': response['razorpay_signature']
    }

    client = razorpay.Client(auth=(keyid, keySecret))

    try:
        status = client.utility.verify_payment_signature(params_dict)
        cold_coffee = ColdCoffe.objects.get(order_id=response['razorpay_order_id'])
        cold_coffee.razorpay_payment_id = response['razorpay_payment_id']
        cold_coffee.paid = True
        cold_coffee.save
        return render(request, 'payment_status.html', {'status': True})
    except:
        return render(request, 'accounts/payment_status.html', {'status': False})


def paltpayment(request):
    keyid = 'rzp_live_Ov8XlxQ15IJQBh'
    keySecret = 'Ke4e8CHQOTIf3CUGLwbwhj0P'
    coldcoffe_data = {
        'name': request.user.username,
        'amount': int("54999") * 1,
    }
    form = CoffeePaymentForm()
    if request.method == "POST":
        name = request.POST.get('name')
        amount = 5499900
        client = razorpay.Client(
            auth=(keyid, keySecret))
        response_payment = client.order.create(dict(amount=amount, currency='INR'))
        order_id = response_payment['id']
        order_status = response_payment['status']
        if order_status == 'created':
            cold_coffee = ColdCoffe(
                name=name,
                amount=amount,
                order_id=order_id,
            )
            cold_coffee.save()
            response_payment['name'] = name
            form = CoffeePaymentForm(request.POST or None)
            return render(request, 'accounts/payment3.html', {'form': form, 'payment': response_payment})

    form = CoffeePaymentForm(initial=coldcoffe_data)
    return render(request, 'accounts/payment3.html', {'form': form})


def expayment(request):
    keyid = 'rzp_live_Ov8XlxQ15IJQBh'
    keySecret = 'Ke4e8CHQOTIf3CUGLwbwhj0P'
    coldcoffe_data = {
        'name': request.user.username,
        'amount': int("81999") * 1,
    }
    form = CoffeePaymentForm()
    if request.method == "POST":
        name = request.POST.get('name')
        amount = 8199900
        client = razorpay.Client(
            auth=(keyid, keySecret))
        response_payment = client.order.create(dict(amount=amount, currency='INR'))
        order_id = response_payment['id']
        order_status = response_payment['status']
        if order_status == 'created':
            cold_coffee = ColdCoffe(
                name=name,
                amount=amount,
                order_id=order_id,
            )
            cold_coffee.save()
            response_payment['name'] = name
            form = CoffeePaymentForm(request.POST or None)
            return render(request, 'accounts/payment4.html', {'form': form, 'payment': response_payment})

    form = CoffeePaymentForm(initial=coldcoffe_data)
    return render(request, 'accounts/payment4.html', {'form': form})


@csrf_exempt
def success(request):
    return render(request, "accounts/success.html")


def activate1(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # return redirect('home')
        return HttpResponse('Thank you for your email confirmation. Now you can login your account.')
    else:
        return HttpResponse('Activation link is invalid!')
    

def activate(request, uid, token):
    try:
        user = User.objects.get(pk=uid)
        verify = Profile.objects.get(user_id=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        verify.is_verify = True
        verify.save()
        return HttpResponse('Thank you for your email confirmation. Now you can <a href="/login" %}"="">login</a> your account.')
    else:
        return HttpResponse('Activation link is invalid!')
