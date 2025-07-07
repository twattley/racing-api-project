from datetime import datetime, timedelta
from fastapi import Depends

import numpy as np
from ..models.service_status import ServiceStatus, IndividualServiceStatus


from ..repository.service_status_repository import (
    ServiceStatusRepository,
    get_service_status_repository,
)
from .base_service import BaseService


class ServiceStatusService(BaseService):
    def __init__(
        self,
        service_status_repository: ServiceStatusRepository,
    ):
        self.service_status_repository = service_status_repository

    async def get_service_status(self) -> ServiceStatus:
        data = await self.service_status_repository.get_service_status()
        data["healthy"] = np.where(
            data["processed_at"] - datetime.now() < timedelta(minutes=2), True, False
        )

        service_status_list = []
        for index, row in data.iterrows():
            service_status_list.append(
                IndividualServiceStatus(
                    job_name=row["service_name"],
                    healthy=row["healthy"],
                )
            )
        return ServiceStatus(service_status=service_status_list)


def get_service_status_service(
    service_status_repository: ServiceStatusRepository = Depends(
        get_service_status_repository
    ),
):
    return ServiceStatusService(service_status_repository)
