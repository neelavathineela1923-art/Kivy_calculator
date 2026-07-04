import sys
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.properties import ListProperty, StringProperty
from kivy.core.window import Window
from kivy.utils import get_color_from_hex, platform
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.graphics import Color, RoundedRectangle

# ONLY set a fixed window size if we are testing on a Desktop environment
if platform not in ('android', 'ios'):
    Window.size = (400, 680)

# ----------------------------------------------------
# THEME CONFIGURATIONS (Hex Colors)
# ----------------------------------------------------
THEMES = {
    "dark": {
        "bg": "#121212",
        "surface": "#1E1E1E",
        "primary": "#00ADB5",
        "text_main": "#EEEEEE",
        "text_sub": "#808080",
        "btn_num": "#2C2C2C",
        "btn_op": "#3A3A3A",
        "btn_accent": "#00ADB5"
    },
    "light": {
        "bg": "#F5F7F8",
        "surface": "#FFFFFF",
        "primary": "#00ADB5",
        "text_main": "#1A1A1A",
        "text_sub": "#7D7D7D",
        "btn_num": "#E4E4E4",
        "btn_op": "#D4D4D4",
        "btn_accent": "#00ADB5"
    }
}

CALC_HISTORY = []

# ----------------------------------------------------
# CUSTOM STYLED WIDGETS
# ----------------------------------------------------
class StyledButton(Button):
    bg_color = ListProperty([1, 1, 1, 1])
    text_color = ListProperty([0, 0, 0, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = [0, 0, 0, 0]
        self.markup = True
        with self.canvas.before:
            self.paint_color = Color(rgba=self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[16])
        self.bind(pos=self.update_canvas, size=self.update_canvas, bg_color=self.update_canvas)

    def update_canvas(self, *args):
        self.paint_color.rgba = self.bg_color
        self.rect.pos = self.pos
        self.rect.size = self.size

class HistoryItem(BoxLayout):
    def __init__(self, expr, res, callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = 70
        self.padding = [10, 5]
        self.expr = expr
        self.res = res
        self.callback = callback

        theme = THEMES[App.get_running_app().current_theme]

        self.expr_label = Label(text=expr, halign='right', valign='middle', color=get_color_from_hex(theme["text_sub"]), font_size='14sp')
        self.expr_label.bind(size=self.expr_label.setter('text_size'))
        
        self.res_label = Button(text=res, halign='right', valign='middle', background_normal='', background_color=[0,0,0,0], color=get_color_from_hex(theme["text_main"]), font_size='18sp')
        self.res_label.bind(size=self.res_label.setter('text_size'))
        self.res_label.bind(on_release=lambda x: self.callback(self.res))

        self.add_widget(self.expr_label)
        self.add_widget(self.res_label)

# ----------------------------------------------------
# SCREENS DEFINITIONS
# ----------------------------------------------------
class CalcScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        theme = THEMES[App.get_running_app().current_theme]
        
        root = BoxLayout(orientation='vertical', padding=15, spacing=10)
        with root.canvas.before:
            self.bg_color = Color(rgba=get_color_from_hex(theme["bg"]))
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        # Navigation row
        nav_bar = BoxLayout(size_hint_y=0.08, spacing=10)
        btn_to_conv = StyledButton(text="[b]Converter[/b]", bg_color=get_color_from_hex(theme["surface"]), text_color=get_color_from_hex(theme["primary"]))
        btn_to_conv.bind(on_release=lambda x: self.switch_screen('converter'))
        
        btn_to_settings = StyledButton(text="[b]Settings ⚙[/b]", bg_color=get_color_from_hex(theme["surface"]), text_color=get_color_from_hex(theme["text_sub"]))
        btn_to_settings.bind(on_release=lambda x: self.switch_screen('settings'))
        
        nav_bar.add_widget(btn_to_conv)
        nav_bar.add_widget(btn_to_settings)
        root.add_widget(nav_bar)

        # History Layout Panel
        self.history_scroll = ScrollView(size_hint_y=0.22, do_scroll_x=False, do_scroll_y=True)
        self.history_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.history_layout.bind(minimum_height=self.history_layout.setter('height'))
        self.history_scroll.add_widget(self.history_layout)
        root.add_widget(self.history_scroll)
        self.refresh_history_ui()

        # Input Display
        display_box = BoxLayout(orientation='vertical', size_hint_y=0.2, padding=10)
        with display_box.canvas.before:
            self.disp_color = Color(rgba=get_color_from_hex(theme["surface"]))
            self.disp_rect = RoundedRectangle(pos=display_box.pos, size=display_box.size, radius=[20])
        display_box.bind(pos=self._update_disp, size=self._update_disp)

        self.display = TextInput(
            text='', multiline=False, readonly=False, halign='right',
            font_size='32sp', background_color=[0,0,0,0],
            foreground_color=get_color_from_hex(theme["text_main"]),
            padding=[10, 20, 10, 10], input_type='number'
        )
        display_box.add_widget(self.display)
        
        action_bar = BoxLayout(size_hint_y=0.05, spacing=20, padding=[10, 0])
        btn_copy = Button(text="Copy", background_normal='', background_color=[0,0,0,0], color=get_color_from_hex(theme["primary"]), font_size='12sp')
        btn_copy.bind(on_release=self.copy_to_clipboard)
        btn_paste = Button(text="Paste", background_normal='', background_color=[0,0,0,0], color=get_color_from_hex(theme["primary"]), font_size='12sp')
        btn_paste.bind(on_release=self.paste_from_clipboard)
        action_bar.add_widget(Label())
        action_bar.add_widget(btn_copy)
        action_bar.add_widget(btn_paste)
        root.add_widget(display_box)
        root.add_widget(action_bar)

        # Keypad Grid
        grid = GridLayout(cols=4, spacing=10, size_hint_y=0.45)
        buttons = [
            ('C', 'op'), ('(', 'op'), (')', 'op'), ('/', 'accent'),
            ('7', 'num'), ('8', 'num'), ('9', 'num'), ('*', 'accent'),
            ('4', 'num'), ('5', 'num'), ('6', 'num'), ('-', 'accent'),
            ('1', 'num'), ('2', 'num'), ('3', 'num'), ('+', 'accent'),
            ('⌫', 'num'), ('0', 'num'), ('.', 'num'), ('=', 'accent')
        ]

        for text, b_type in buttons:
            if b_type == 'num':
                bg = get_color_from_hex(theme["btn_num"])
                tc = get_color_from_hex(theme["text_main"])
            elif b_type == 'op':
                bg = get_color_from_hex(theme["btn_op"])
                tc = get_color_from_hex(theme["primary"])
            else:
                bg = get_color_from_hex(theme["btn_accent"])
                tc = get_color_from_hex("#FFFFFF")

            btn = StyledButton(text=f"[size=22sp]{text}[/size]", bg_color=bg, text_color=tc)
            btn.bind(on_release=self.on_btn_press)
            grid.add_widget(btn)

        root.add_widget(grid)
        self.add_widget(root)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_disp(self, instance, value):
        self.disp_rect.pos = instance.pos
        self.disp_rect.size = instance.size

    def on_btn_press(self, instance):
        text = instance.text.replace("[size=22sp]", "").replace("[/size]", "")
        current = self.display.text

        if text == 'C':
            self.display.text = ''
        elif text == '⌫':
            self.display.text = current[:-1]
        elif text == '=':
            try:
                expr = current.replace('×', '*').replace('÷', '/')
                if expr:
                    result = str(eval(expr))
                    if '.' in result and len(result) > 10:
                        result = f"{float(result):.6f}".rstrip('0').rstrip('.')
                    CALC_HISTORY.append((current, result))
                    self.display.text = result
                    self.refresh_history_ui()
            except Exception:
                self.display.text = 'Error'
        else:
            self.display.text += text

    def copy_to_clipboard(self, instance):
        if self.display.text:
            Clipboard.copy(self.display.text)

    def paste_from_clipboard(self, instance):
        self.display.text += Clipboard.paste()

    def append_history_to_input(self, val):
        self.display.text += val

    def refresh_history_ui(self):
        self.history_layout.clear_widgets()
        for expr, res in reversed(CALC_HISTORY):
            self.history_layout.add_widget(HistoryItem(expr, res, self.append_history_to_input))

    def switch_screen(self, name):
        self.manager.current = name


class ConverterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.categories = {
            "Length": {"Meters": 1, "Kilometers": 0.001, "Centimeters": 100, "Miles": 0.000621371, "Feet": 3.28084, "Inches": 39.3701},
            "Mass": {"Kilograms": 1, "Grams": 1000, "Pounds": 2.20462, "Ounces": 35.274},
            "Volume": {"Liters": 1, "Milliliters": 1000, "Gallons": 0.264172, "Cups": 4.22675},
            "Temperature": {"Celsius": "C", "Fahrenheit": "F", "Kelvin": "K"}
        }
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        theme = THEMES[App.get_running_app().current_theme]
        
        root = BoxLayout(orientation='vertical', padding=20, spacing=15)
        with root.canvas.before:
            self.bg_color = Color(rgba=get_color_from_hex(theme["bg"]))
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        header = BoxLayout(size_hint_y=0.08, spacing=10)
        btn_back = StyledButton(text="[b]← Calculator[/b]", bg_color=get_color_from_hex(theme["surface"]), text_color=get_color_from_hex(theme["primary"]))
        btn_back.bind(on_release=lambda x: self.switch_screen('calculator'))
        header.add_widget(btn_back)
        root.add_widget(header)

        root.add_widget(Label(text="Select Category", color=get_color_from_hex(theme["text_sub"]), size_hint_y=0.04, halign='left'))
        self.cat_spinner = Spinner(text="Length", values=list(self.categories.keys()), size_hint_y=0.08, background_color=get_color_from_hex(theme["surface"]), color=get_color_from_hex(theme["text_main"]))
        self.cat_spinner.bind(text=self.update_units)
        root.add_widget(self.cat_spinner)

        root.add_widget(Label(text="From Value & Unit", color=get_color_from_hex(theme["text_sub"]), size_hint_y=0.04))
        input_row = BoxLayout(spacing=10, size_hint_y=0.1)
        self.input_val = TextInput(text='1', multiline=False, background_color=get_color_from_hex(theme["surface"]), foreground_color=get_color_from_hex(theme["text_main"]), font_size='20sp', input_type='number')
        self.input_val.bind(text=self.perform_conversion)
        
        self.from_spinner = Spinner(text="Meters", values=list(self.categories["Length"].keys()), background_color=get_color_from_hex(theme["surface"]), color=get_color_from_hex(theme["text_main"]))
        self.from_spinner.bind(text=self.perform_conversion)
        
        input_row.add_widget(self.input_val)
        input_row.add_widget(self.from_spinner)
        root.add_widget(input_row)

        root.add_widget(Label(text="To Unit & Result", color=get_color_from_hex(theme["text_sub"]), size_hint_y=0.04))
        output_row = BoxLayout(spacing=10, size_hint_y=0.1)
        self.output_val = TextInput(text='', multiline=False, readonly=True, background_color=get_color_from_hex(theme["surface"]), foreground_color=get_color_from_hex(theme["primary"]), font_size='20sp')
        
        self.to_spinner = Spinner(text="Kilometers", values=list(self.categories["Length"].keys()), background_color=get_color_from_hex(theme["surface"]), color=get_color_from_hex(theme["text_main"]))
        self.to_spinner.bind(text=self.perform_conversion)
        
        output_row.add_widget(self.output_val)
        output_row.add_widget(self.to_spinner)
        root.add_widget(output_row)

        action_bar = BoxLayout(size_hint_y=0.05, spacing=20)
        btn_copy = Button(text="Copy Output", background_normal='', background_color=[0,0,0,0], color=get_color_from_hex(theme["primary"]))
        btn_copy.bind(on_release=lambda x: Clipboard.copy(self.output_val.text) if self.output_val.text else None)
        action_bar.add_widget(Label())
        action_bar.add_widget(btn_copy)
        root.add_widget(action_bar)
        root.add_widget(BoxLayout(size_hint_y=0.3))

        self.add_widget(root)
        Clock.schedule_once(lambda dt: self.perform_conversion())

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def update_units(self, spinner, text):
        units = list(self.categories[text].keys())
        self.from_spinner.values = units
        self.to_spinner.values = units
        self.from_spinner.text = units[0]
        self.to_spinner.text = units[1] if len(units) > 1 else units[0]
        self.perform_conversion()

    def perform_conversion(self, *args):
        cat = self.cat_spinner.text
        from_u = self.from_spinner.text
        to_u = self.to_spinner.text
        val_str = self.input_val.text

        if not val_str:
            self.output_val.text = ""
            return

        try:
            val = float(val_str)
        except ValueError:
            self.output_val.text = "Invalid Input"
            return

        if cat == "Temperature":
            if from_u == to_u: res = val
            elif from_u == "Celsius" and to_u == "Fahrenheit": res = (val * 9/5) + 32
            elif from_u == "Celsius" and to_u == "Kelvin": res = val + 273.15
            elif from_u == "Fahrenheit" and to_u == "Celsius": res = (val - 32) * 5/9
            elif from_u == "Fahrenheit" and to_u == "Kelvin": res = (val - 32) * 5/9 + 273.15
            elif from_u == "Kelvin" and to_u == "Celsius": res = val - 273.15
            elif from_u == "Kelvin" and to_u == "Fahrenheit": res = (val - 273.15) * 9/5 + 32
        else:
            base_val = val / self.categories[cat][from_u]
            res = base_val * self.categories[cat][to_u]

        self.output_val.text = f"{res:.5f}".rstrip('0').rstrip('.')

    def switch_screen(self, name):
        self.manager.current = name


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()
        theme = THEMES[App.get_running_app().current_theme]
        
        root = BoxLayout(orientation='vertical', padding=20, spacing=20)
        with root.canvas.before:
            self.bg_color = Color(rgba=get_color_from_hex(theme["bg"]))
            self.bg_rect = RoundedRectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        header = BoxLayout(size_hint_y=0.08)
        btn_back = StyledButton(text="[b]← Back[/b]", bg_color=get_color_from_hex(theme["surface"]), text_color=get_color_from_hex(theme["primary"]))
        btn_back.bind(on_release=lambda x: self.switch_screen('calculator'))
        header.add_widget(btn_back)
        root.add_widget(header)

        root.add_widget(Label(text="Theme Options", color=get_color_from_hex(theme["text_main"]), font_size='18sp', bold=True, size_hint_y=0.05))
        
        theme_row = BoxLayout(spacing=15, size_hint_y=0.08)
        btn_dark = StyledButton(text="Dark Theme", bg_color=get_color_from_hex(theme["btn_num"]) if App.get_running_app().current_theme == 'light' else get_color_from_hex(theme["primary"]), text_color=get_color_from_hex(theme["text_main"]))
        btn_dark.bind(on_release=lambda x: self.change_theme('dark'))
        
        btn_light = StyledButton(text="Light Theme", bg_color=get_color_from_hex(theme["btn_num"]) if App.get_running_app().current_theme == 'dark' else get_color_from_hex(theme["primary"]), text_color=get_color_from_hex(theme["text_main"]))
        btn_light.bind(on_release=lambda x: self.change_theme('light'))
        
        theme_row.add_widget(btn_dark)
        theme_row.add_widget(btn_light)
        root.add_widget(theme_row)

        root.add_widget(Label(text="Data Management", color=get_color_from_hex(theme["text_main"]), font_size='18sp', bold=True, size_hint_y=0.05))
        btn_clear = StyledButton(text="Clear Calculation History", bg_color=get_color_from_hex("#D9534F"), text_color=get_color_from_hex("#FFFFFF"), size_hint_y=0.08)
        btn_clear.bind(on_release=self.clear_history)
        root.add_widget(btn_clear)

        root.add_widget(Label(text="About App", color=get_color_from_hex(theme["text_main"]), font_size='18sp', bold=True, size_hint_y=0.05))
        about_box = BoxLayout(orientation='vertical', padding=15, size_hint_y=0.25)
        with about_box.canvas.before:
            self.about_color = Color(rgba=get_color_from_hex(theme["surface"]))
            self.about_rect = RoundedRectangle(pos=about_box.pos, size=about_box.size, radius=[15])
        about_box.bind(pos=self._update_about, size=self._update_about)
        
        about_box.add_widget(Label(text="Professional Utility Suite v1.1", color=get_color_from_hex(theme["text_main"]), bold=True, font_size='15sp'))
        about_box.add_widget(Label(text="Engineered with clean adaptive layouts and real-time unit data parsing calculations.", color=get_color_from_hex(theme["text_sub"]), font_size='13sp', halign='center'))
        
        root.add_widget(about_box)
        root.add_widget(BoxLayout(size_hint_y=0.15))
        self.add_widget(root)

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _update_about(self, instance, value):
        self.about_rect.pos = instance.pos
        self.about_rect.size = instance.size

    def change_theme(self, target_theme):
        App.get_running_app().current_theme = target_theme
        for screen in self.manager.screens:
            screen.build_ui()

    def clear_history(self, instance):
        global CALC_HISTORY
        CALC_HISTORY = []
        self.manager.get_screen('calculator').refresh_history_ui()

    def switch_screen(self, name):
        self.manager.current = name


# ----------------------------------------------------
# MAIN APPLICATION ENGINE
# ----------------------------------------------------
class ProfessionalCalcApp(App):
    current_theme = StringProperty("dark")

    def build(self):
        self.title = "Universal Professional Calculator"
        sm = ScreenManager(transition=FadeTransition(duration=0.15))
        sm.add_widget(CalcScreen(name='calculator'))
        sm.add_widget(ConverterScreen(name='converter'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm

if __name__ == '__main__':
    ProfessionalCalcApp().run()
