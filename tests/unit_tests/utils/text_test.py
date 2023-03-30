from sciety_labs.utils.text import remove_markup


class TestRemoveMarkup:
    def test_should_remove_markup(self):
        assert remove_markup('<i>italic</i> text') == 'italic text'
