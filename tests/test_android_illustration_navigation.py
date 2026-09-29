"""A tutorial drawing must never be mistaken for an actionable native button."""
from tools.check_android_simulation_ui import button_coordinates


def test_next_taps_real_footer_instead_of_the_illustrated_label(tmp_path, capsys):
    page = tmp_path / 'guide.xml'
    page.write_text('''<hierarchy><node package="com.aqss.bodyguard.prototype" bounds="[0,0][1000,2000]">
        <node package="com.aqss.bodyguard.prototype" class="android.widget.TextView" text="Next" clickable="false" bounds="[100,700][500,800]" />
        <node package="com.aqss.bodyguard.prototype" class="android.widget.Button" text="Next" clickable="true" enabled="true" bounds="[400,1800][900,1900]" />
    </node></hierarchy>''')
    button_coordinates(str(page), 'Next')
    assert capsys.readouterr().out.strip() == '650 1850'
