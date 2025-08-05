from .base_entity import BaseEntity


class IndividualServiceStatus(BaseEntity):
    job_name: str
    healthy: bool


class ServiceStatus(BaseEntity):
    service_status: list[IndividualServiceStatus]
