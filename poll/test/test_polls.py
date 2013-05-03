from datetime import datetime
from unittest import TestCase
from django.conf import settings
from nose.tools import nottest

from poll.models import Poll, Response
from django.contrib.auth.models import User
from rapidsms.models import Contact, Backend, Connection
from rapidsms_httprouter.models import MessageBatch
from rapidsms_httprouter.router import get_router
from dateutil.relativedelta import relativedelta


class TestBatchSending(TestCase):

    def setUp(self):
        self.clear_settings()

    def tearDown(self):
        self.clear_settings()

    def test_should_choose_batch_status_based_on_feature_flag(self):
        p = Poll()

        self.assertEqual(p.get_start_poll_batch_status(), "Q")

        settings.FEATURE_PREPARE_SEND_POLL = True

        self.assertEqual(p.get_start_poll_batch_status(), "P")

        settings.FEATURE_PREPARE_SEND_POLL = False

        self.assertEqual(p.get_start_poll_batch_status(), "Q")

    def test_batch_status_should_be_Q_by_default(self):
        poll = self.create_and_start_poll("Q")

        batch = MessageBatch.objects.filter(name=poll.get_outgoing_message_batch_name()).all()[0]

        self.assertEqual(batch.status, "Q")

    def test_batch_status_should_be_P_if_feature_flag_is_on(self):
        settings.FEATURE_PREPARE_SEND_POLL = True

        poll = self.create_and_start_poll("P")

        batch = MessageBatch.objects.filter(name=poll.get_outgoing_message_batch_name()).all()[0]

        self.assertEqual(batch.status, "P")

    def test_should_be_ready_to_send_if_batches_are_queued(self):
        settings.FEATURE_PREPARE_SEND_POLL = True

        poll = self.create_and_start_poll("RTS")

        self.assertEqual(poll.is_ready_to_send(), True)

    def create_and_start_poll(self, uniqueness):
        poll_user = User.objects.create(username="TBS_USER_POLL" + uniqueness, email='foo@foo.com')
        contact_user = User.objects.create(username="TBS_USER_CONTACT" + uniqueness, email='foo@foo.com')

        poll = Poll.objects.create(name="TBS_POLL" + uniqueness, question='test_batch_sending', type=Poll.TYPE_TEXT, user=poll_user)

        female_contact = Contact.objects.create(name="TBS_CONTACT" + uniqueness, gender='F', user=contact_user, birthdate=datetime.now() - relativedelta(years=25))
        backend = Backend.objects.create(name="TBS" + uniqueness)
        connection_for_female = Connection.objects.create(identity='08883338', backend=backend)
        connection_for_female.contact = female_contact
        connection_for_female.save()
        poll.contacts.add(female_contact)
        poll.add_yesno_categories()
        poll.save()
        poll.start()
        return poll



    def clear_settings(self):
        try:
            delattr(settings, "FEATURE_PREPARE_SEND_POLL")
        except AttributeError:
            pass



class TestPolls(TestCase):

    def setUp(self):
        self.male_user = User.objects.create(username='fred', email='shaggy@scooby.com')
        self.female_user = User.objects.create(username='scrapy', email='shaggy@scooby.com')
        self.poll = Poll.objects.create(name='test poll', question='are you happy', user=self.male_user, type=Poll.TYPE_TEXT)

        self.male_contact = Contact.objects.create(name='shaggy', user=self.male_user, gender='M',birthdate=datetime.now() - relativedelta(years=20))
        self.female_contact = Contact.objects.create(name='dafny', user=self.female_user, gender='F',birthdate=datetime.now() - relativedelta(years=25))

        self.backend = Backend.objects.create(name='scoobydoo')

        self.connection_for_male = Connection.objects.create(identity='0794339344', backend=self.backend)
        self.connection_for_male.contact = self.male_contact
        self.connection_for_male.save()

        self.connection_for_female = Connection.objects.create(identity='0794339345', backend=self.backend)
        self.connection_for_female.contact = self.female_contact
        self.connection_for_female.save()

        self.poll.contacts.add(self.female_contact)
        self.poll.contacts.add(self.male_contact)
        self.poll.add_yesno_categories()
        self.poll.save()
        self.poll.start()

    def tearDown(self):
        Backend.objects.all().delete()
        Connection.objects.all().delete()
        Response.objects.all().delete()
        Poll.objects.all().delete()
        Contact.objects.all().delete()
        User.objects.all().delete()

    def test_responses_by_gender_only_for_male(self):
        self.send_message(self.connection_for_male, 'yes')

        yes_aggregation = [1, u"yes" ]

        filtered_responses = self.poll.responses_by_gender(gender='m')
        self.assertIn(yes_aggregation, filtered_responses)

    def test_responses_by_gender(self):
        self.send_message(self.connection_for_male, 'yes')
        self.send_message(self.connection_for_female, 'No')

        no_aggregation = [1, u"no" ]
        filtered_responses = self.poll.responses_by_gender(gender='F')

        self.assertIn(no_aggregation, filtered_responses)

    def test_responses_by_gender_should_check_if_poll_is_yes_no(self):
        poll = Poll.objects.create(name='test poll2', question='are you happy??', user=self.male_user, type=Poll.TYPE_TEXT)
        with(self.assertRaises(AssertionError)):
            poll.responses_by_gender(gender='F')

    def test_responses_by_age(self):
        self.send_message(self.connection_for_male,'yes')
        self.send_message(self.connection_for_female,'no')
        self.send_message(self.connection_for_male,'foobar')

        yes_responses = [1, u"yes" ]
        no_responses = [1, u"no" ]
        unknown_responses = [1, u"unknown" ]

        results = self.poll.responses_by_age(20, 26)

        self.assertIn(yes_responses,results)
        self.assertIn(no_responses,results)
        self.assertIn(unknown_responses,results)

    def test_message_batch_has_poll_id_in_name(self):
        batchName = self.poll.get_outgoing_message_batch_name()
        batchesForPoll = MessageBatch.objects.filter(name=batchName).all()

        self.assertEqual(len(batchesForPoll), 1, "Should be able to find a message batch with name [%s]." % batchName)

    def send_message(self, connection, message):
        router = get_router()
        router.handle_incoming(connection.backend.name, connection.identity, message)
