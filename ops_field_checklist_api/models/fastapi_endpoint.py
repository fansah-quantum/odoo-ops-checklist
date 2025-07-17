from odoo import api, fields, models
from fastapi.middleware.cors import CORSMiddleware

from ..routers import router as checklist_router

APP_NAME = "terminal_checklist_api"


class FastapiEndpoint(models.Model):
    _inherit = "fastapi.endpoint"

    app: str = fields.Selection(
        selection_add=[(APP_NAME, "Terminal Checklist")],
        ondelete={APP_NAME: "cascade"},
    )
    server_api_key = fields.Char()

    @api.model
    def _get_fastapi_routers(self):
        if self.app == APP_NAME:
            return [checklist_router]
        return super()._get_fastapi_routers()

    def _get_app(self):
        app = super()._get_app()
        if self.app == APP_NAME:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        return app
