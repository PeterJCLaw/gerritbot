
from nose import with_setup

import helpers

@with_setup(helpers.clear_messages, helpers.clear_messages)
def test_samples():
    def check(name, expected_message):
        helpers.trigger_from_file('sample-{0}.json'.format(name))
        message = helpers.last_message()

        message = helpers.text_only(message)

        assert expected_message == message

    yield check, "abandon", "PeterJCLaw abandoned their change on test(master) : Remove file to create conflict with Andy's #138. http://example.com/155"
    yield check, "merge", "Applied PeterJCLaw's change on gerritbot(master) : Add a dev helper script. http://example.com/45"
    yield check, "push", "plaw submitted test(master) : CHEEEEEESE http://example.com/32"
    yield check, "push-else", "PeterJCLaw updated cyanide(master) : Bump pyenv for webcam calibration. http://example.com/87"
    yield check, "review", "plaw reviewed test(master) : CHEEEEEESE http://example.com/32"
    yield check, "update-ref", "PeterJCLaw updated test/other(master) from 6b3a9a1 to 6daf656 : http://example.com/cgit/test/other.git"
