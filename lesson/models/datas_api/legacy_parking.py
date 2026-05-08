# -*- coding: utf-8 -*-
"""Legacy Parking API - 车辆进出相关接口。

Batch40: 从 datas_api_legacy.py 拆分 vehicle-inout 逻辑。
"""

from fastapi import APIRouter, Depends

from models.datas_api.moral.api_permission import unified_api_permission
from models.parking import get_parking_records


router = APIRouter()


@router.get(
    "/vehicle-inout/{counts}",
    dependencies=[Depends(unified_api_permission("/api/vehicle-inout/{counts}"))],
)
async def get_vehicle_inout(counts: int = 20):
    """获取所有车辆进出记录"""
    return get_parking_records(counts)
