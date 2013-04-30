# -*- coding: utf-8 -*-
import rapidsms
import datetime

from rapidsms.apps.base import AppBase
from .models import Poll
from django.db.models import Q
from rapidsms_httprouter.models import Message,MessageBatch

import logging
log = logging.getLogger(__name__)

class App(AppBase):
    def respond_to_message(self,message,response_msg,poll):

        if response_msg == poll.default_response:
            try:
                batch=MessageBatch.objects.get(name=str(poll.pk))
                batch.status="Q"
                batch.save()
                msg=Message.objects.create(text=response_msg,status="Q",connection=message.connection,direction="O",in_response_to=message.db_message)
                batch.messages.add(msg)
            except MessageBatch.DoesNotExist:
                message.respond(response_msg)
        else:
            message.respond(response_msg)


    def handle (self, message):
        # see if this contact matches any of our polls
        if message.connection is not None and message.db_message.pk:
            log.debug("[poll-app] [{}] Handling incoming message [pk={}]...".format(message.connection.identity, message.db_message.pk))

        if message.db_message is None:
            log.debug("[poll-app] Incoming message doesn't have a db message!!")

        if (message.connection.contact):
            try:
                poll = Poll.objects.filter(contacts=message.connection.contact).exclude(start_date=None)\
                    .filter(Q(end_date=None) | (~Q(end_date=None) & Q(end_date__gt=datetime.datetime.now())))\
                    .latest('start_date')

                log.debug("[poll-app] Found poll for message [{}]".format(str(poll)))

                if  poll.responses.filter(contact=message.connection.contact).exists():
                    old_response=poll.responses.filter(contact=message.connection.contact)[0]
                    log.debug("[poll-app] Processing response again (theres already one from this contact)")
                    response_obj, response_msg = poll.process_response(message)
                    if poll.response_type == Poll.RESPONSE_TYPE_ONE :
                        log.debug("[poll-app] Poll only allows one response per person, overwriting old response...")
                        if not response_obj.has_errors or old_response.has_errors:
                            old_response.delete()
                            if hasattr(message, 'db_message'):
                                db_message = message.db_message
                                db_message.handled_by = 'poll'
                                db_message.save()
                            if response_msg and response_msg.strip():
                                self.respond_to_message(message,response_msg,poll)
                        else:
                            response_obj.delete()
                        return False
                    else:
                        return False

                else:
                    log.debug("[poll-app] Processing message and replying to sender...")
                    response_obj, response_msg = poll.process_response(message)
                    if hasattr(message, 'db_message'):
                        # if no other app handles this message, we want
                        # the handled_by field set appropriately,
                        # it won't since this app returns false
                        db_message = message.db_message
                        db_message.handled_by = 'poll'
                        db_message.save()
                    if response_msg and response_msg.strip():
                        self.respond_to_message(message,response_msg,poll)
                    elif poll.default_response :
                        #send default response anyway even for errors
                        self.respond_to_message(message,poll.default_response,poll)

                    log.debug("[poll-app] Message handled.")
                    # play nice, let other things handle responses
                    return False
            except Poll.DoesNotExist:
                if message.connection is not None:
                    log.debug("[poll-app] [%s] Poll not found for this message" % message.connection.identity)
                else:
                    log.debug("[poll-app] Poll not found for this message, and there is no connection either")
                pass
            log.debug("[poll-app] Handled.")
        return False