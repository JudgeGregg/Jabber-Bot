#file-encoding: utf-8
"""Jabber Bot for sending announcements to users."""

from twisted.application import service
from twisted.python import log
from twisted.words.protocols.jabber.jid import JID
from twisted.words.protocols.jabber.xmlstream import IQ
from twisted.words.xish import domish
from wokkel.client import XMPPClient
from wokkel.subprotocols import IQHandlerMixin
from wokkel.xmppim import MessageProtocol, AvailablePresence
from wokkel.data_form import Field, Form

from auth import SERV_ID, BOT_ID, BOT_SECRET

NS_COMMAND = 'http://jabber.org/protocol/commands'
BROADCAST_NODE = 'http://jabber.org/protocol/admin#announce'
FORM_TYPE_VALUE = 'http://jabber.org/protocol/admin'
LOG_TRAFFIC = True
SERV_JID = JID(SERV_ID)
BOT_JID = JID(BOT_ID)


class IQClient(MessageProtocol, IQHandlerMixin):
    """Base Handler for sending and receiving IQ stanzas."""

    iqHandlers = {"/iq[@type='result']": 'on_result'}
    subject_value = 'Test Announcement'
    body_values = ['Test Announcement']

    def create_form(self):
        """Create announce form."""
        subject_form_field = Field(var='subject', value=self.subject_value)
        announce_form_field = Field(fieldType='text-multi', var='body',
                                    values=self.body_values)
        form = Form('submit')
        form.addField(subject_form_field)
        form.addField(announce_form_field)
        return form

    def create_request(self, mode):
        """Create IQ request.
        @param mode: request mode (get or set)
        @type mode: string
        """
        request = IQ(self.xmlstream, mode)
        return request

    def on_result(self, res):
        """Callback for result IQs.
        @param res: IQ received
        @type res: domish.Element
        """
        command = res.firstChildElement()
        if command[u'status'] == u'executing':
            session_id = command[u'sessionid']
            request = self.create_request('get')
            broad = request.addElement((NS_COMMAND, 'command'))
            broad['sessionid'] = session_id
            broad['node'] = BROADCAST_NODE
            form = self.create_form()
            broad.addChild(form.toElement())
            request.send(SERV_JID.full())
        else:
            log.msg('Announce sent.')

    def send_announce(self, subject, body):
        """Initialise broadcast.
        @param subject: announce subject
        @type subject: string
        @param body: announce body
        @type body: list of strings
        """
        request = self.create_request('set')
        broad = request.addElement((NS_COMMAND, 'command'))
        broad['node'] = BROADCAST_NODE
        broad['action'] = 'execute'
        self.subject_value = subject
        self.body_values = body
        log.msg('Sending announce.')
        request.send(SERV_JID.full())

    def onMessage(self, msg):
        """Callback on message received."""
        log.msg(str(msg))

    def send_message(self, to_, body):
        """Send a message.
        @param to: message recipient
        @type to: JID
        @param body: announce body
        @type body: string
        """
        message = domish.Element((None, "message"))
        message["to"] = to_.full()
        message["type"] = 'chat'
        message.addElement("body", content=str(body))
        self.send(message)

    def connectionInitialized(self):
        """Register results IQs to callback."""
        log.msg('Connection Initialized')
        self.send(AvailablePresence())
        self.xmlstream.addObserver("/iq[@type='result']", self.handleRequest)
        self.xmlstream.addObserver("/message", self._onMessage)

application = service.Application('Jabber Bot')

client = XMPPClient(BOT_JID, BOT_SECRET)
client.logTraffic = LOG_TRAFFIC
client.setServiceParent(application)

IQHandler = IQClient()
IQHandler.setHandlerParent(client)
