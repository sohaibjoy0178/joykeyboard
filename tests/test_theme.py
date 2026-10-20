import pytest


def contrast(foreground, background):
    def luminance(color):
        rgb = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055)**2.4 for value in rgb]
        return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))
    high, low = sorted([luminance(foreground), luminance(background)], reverse=True)
    return (high + .05) / (low + .05)


@pytest.mark.parametrize("foreground,background", [
    ("#172337", "#EEF2F7"), ("#526279", "#EEF2F7"), ("#455A76", "#E5EDF9"),
    ("#FFFFFF", "#1A70D2"), ("#FFFFFF", "#1266C8"), ("#982638", "#FCE7EA"),
    ("#AE2638", "#F1F6FE"), ("#095CBF", "#EDF3FC"),
    ("#172337", "#9B9B9B"), ("#172337", "#F5FAFF"),
    ("#FFFFFF", "#0C66CD"), ("#AE2638", "#F5FAFF"),
    ("#FFF0F4", "#686B70"), ("#EDF2FA", "#686B70"), ("#FFABB8", "#292F39"), ("#FFBCC8", "#4B2531"),
])
def test_primary_text_and_glass_states_have_readable_contrast(foreground, background):
    assert contrast(foreground, background) >= 4.5
