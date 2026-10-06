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


def test_resume_guide_taps_footer_above_system_navigation(tmp_path, capsys):
    page = tmp_path / 'resume.xml'
    page.write_text('''<hierarchy><node package="com.aqss.bodyguard.prototype" bounds="[0,0][1440,2910]">
        <node package="com.aqss.bodyguard.prototype" class="android.widget.Button" text="Resume guide" clickable="true" enabled="true" bounds="[406,2742][1384,2910]" />
    </node></hierarchy>''')
    button_coordinates(str(page), 'Resume guide')
    assert capsys.readouterr().out.strip() == '895 2826'


def test_custom_help_dialog_allows_its_visible_bottom_action(tmp_path, capsys):
    page = tmp_path / 'custom-dialog.xml'
    page.write_text('''<hierarchy><node package="com.aqss.bodyguard.prototype" resource-id="android:id/customPanel" bounds="[60,550][900,1480]">
        <node package="com.aqss.bodyguard.prototype" class="android.widget.Button" text="Show voice steps" clickable="true" enabled="true" bounds="[110,1330][850,1440]" />
    </node></hierarchy>''')
    button_coordinates(str(page), 'Show voice steps')
    assert capsys.readouterr().out.strip() == '480 1385'


def test_page_content_at_system_navigation_edge_is_not_tapped(tmp_path, capsys):
    page = tmp_path / 'page.xml'
    page.write_text('''<hierarchy><node package="com.aqss.bodyguard.prototype" bounds="[0,0][1000,2000]">
        <node package="com.aqss.bodyguard.prototype" class="android.widget.Button" text="Show voice steps" clickable="true" enabled="true" bounds="[100,1850][900,2000]" />
    </node></hierarchy>''')
    button_coordinates(str(page), 'Show voice steps')
    assert capsys.readouterr().out == ''


def test_custom_dialog_does_not_tap_a_zero_size_offscreen_action(tmp_path, capsys):
    page = tmp_path / 'offscreen-dialog.xml'
    page.write_text('''<hierarchy><node package="com.aqss.bodyguard.prototype" resource-id="android:id/customPanel" bounds="[60,550][900,1480]">
        <node package="com.aqss.bodyguard.prototype" class="android.widget.Button" text="Show voice steps" clickable="true" enabled="true" bounds="[0,0][0,0]" />
    </node></hierarchy>''')
    button_coordinates(str(page), 'Show voice steps')
    assert capsys.readouterr().out == ''
