from shiny import App

import server
import ui

app = App(ui.app_ui, server.server)