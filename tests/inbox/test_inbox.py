# vim: fileencoding=utf-8 et ts=4 sts=4 sw=4 tw=0

from solariat_bottle.db.channel.base   import create_outbound_post

from solariat_bottle.tests.slow.test_conversations import ConversationBaseCase


class InboxCase(ConversationBaseCase):

    def test_faked_response(self):

        post = self._create_tweet(
            user_profile=self.contact,
            channels=[self.inbound],
            content="I need a laptop")

        reply = create_outbound_post(self.user,
                                     self.outbound,
                                     "Here - try this one",
                                     post)

        self.assertEqual(reply.parent.id, post.id)
        post.reload()
        self.assertEqual(post.channel_assignments[str(self.inbound.id)], 'replied')

