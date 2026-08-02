from fastapi import APIRouter, HTTPException, Request, Response, status

from replaytutor.config import Settings
from replaytutor.contracts import (
    ChartTool,
    ChartToolManifestListResponse,
    ChartToolPreference,
    ChartToolPreferenceListResponse,
    ChartToolTemplate,
    ChartToolTemplateListResponse,
    CreateChartToolTemplateRequest,
    UpdateChartToolPreferenceRequest,
)
from replaytutor.modules.chart_tools import ChartToolService

router = APIRouter(prefix="/api/v1/chart-tools", tags=["chart-tools"])


def service(request: Request) -> ChartToolService:
    settings: Settings = request.app.state.settings
    return ChartToolService(settings)


@router.get("", response_model=ChartToolManifestListResponse)
def list_chart_tools(request: Request) -> ChartToolManifestListResponse:
    return service(request).manifests()


@router.get("/templates", response_model=ChartToolTemplateListResponse)
def list_templates(request: Request) -> ChartToolTemplateListResponse:
    return service(request).list_templates()


@router.post("/templates", response_model=ChartToolTemplate)
def create_template(
    request: Request,
    payload: CreateChartToolTemplateRequest,
) -> ChartToolTemplate:
    return service(request).create_template(payload)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(request: Request, template_id: str) -> Response:
    try:
        service(request).delete_template(template_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/preferences", response_model=ChartToolPreferenceListResponse)
def list_preferences(request: Request) -> ChartToolPreferenceListResponse:
    return service(request).list_preferences()


@router.put("/preferences/{tool}", response_model=ChartToolPreference)
def update_preference(
    request: Request,
    tool: ChartTool,
    payload: UpdateChartToolPreferenceRequest,
) -> ChartToolPreference:
    try:
        return service(request).update_preference(tool, payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
