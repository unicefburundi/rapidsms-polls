#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
Created on May 28, 2013

@author: raybesiga
'''
from django.core.management.base import BaseCommand
import traceback

from poll.models import Poll
from unregister.models import Blacklist
from django.conf import settings

from optparse import make_option
from poll.forms import NewPollForm
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from rapidsms.models import Contact
from django.db.models import Q


class Command(BaseCommand):
    help = "Create school enrollment termly polls"

    option_list = BaseCommand.option_list + (
        make_option('-n', '--name', dest='n'),
        make_option('-t', '--poll_type', dest='t'),
        make_option('-q', '--question', dest='q'),
        make_option('-r', '--default_response', dest='r'),
        make_option('-c', '--contacts', dest='c'),
        make_option('-u', '--user', dest='u'),
        make_option('-s', '--start_immediately', dest='s'),
        make_option('-e', '--response_type', dest='e'),
        make_option('-g', '--groups', dest='g'),
        )

    def handle(self, **options):
        total_enrollment_girls = Poll.objects.create(
                name="total_enrollment_girls",
                type="n",
                question="What is the total number of ALL girls enrolled in school this term? Answer in figures e.g. 150",
                default_response='',
                user=User.objects.get(username='admin'),
                )
        total_enrollment_girls.sites.add(Site.objects.get_current())
        
        total_enrollment_boys = Poll.objects.create(
                name="total_enrollment_boys",
                type="n",
                question="What is the total number of ALL boys enrolled in school this term? Answer in figures e.g. 150",
                default_response='',
                user = User.objects.get(username='admin'),
                )
        total_enrollment_boys.sites.add(Site.objects.get_current())