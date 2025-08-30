"""
Chain2Gate SDK - A powerful single-class SDK for Chain2Gate IoT energy monitoring API
"""
import requests
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Status(Enum):
    PENDING = "PENDING"
    AWAITING = "AWAITING"
    ADMISSIBLE = "ADMISSIBLE"
    NOT_ADMISSIBLE = "NOT_ADMISSIBLE"
    REFUSED = "REFUSED"
    ASSOCIATED = "ASSOCIATED"
    TAKEN_IN_CHARGE = "TAKEN_IN_CHARGE"
    DISASSOCIATED = "DISASSOCIATED"


class PodMType(Enum):
    M1 = "M1"  # Consumption meter
    M2 = "M2"  # Production meter
    M2_2 = "M2_2"
    M2_3 = "M2_3"
    M2_4 = "M2_4"


class UserType(Enum):
    PROSUMER = "PROSUMER"
    CONSUMER = "CONSUMER"


class DeviceType(Enum):
    PLUG = "PLUG"
    METER_MONOFASE = "METER_MONOFASE"
    METER_TRIFASE = "METER_TRIFASE"
    DIN = "DIN"
    DIN_MODBUS = "DIN_MODBUS"
    ENGINE = "ENGINE"
    DIN_ETHERNET = "DIN_ETHERNET"
    METER_1P_MODBUS = "METER_1P_MODBUS"
    METER_3P_MODBUS = "METER_3P_MODBUS"
    METER_3P_MODBUS_LTE = "METER_3P_MODBUS_LTE"


@dataclass
class AdmissibilityRequest:
    id: str
    pod: str
    status: Status
    message: str
    fiscal_code: str
    closed_at: Optional[str]
    created_at: str
    updated_at: str
    group: str


@dataclass
class AssociationRequest:
    id: str
    pod: str
    serial: str
    request_type: str
    pod_m_type: PodMType
    user_type: UserType
    first_name: str
    last_name: str
    email: str
    contract_signed: bool
    product: str
    status: Status
    message: str
    fiscal_code: str
    closed_at: Optional[str]
    created_at: str
    updated_at: str
    group: str


@dataclass
class DisassociationRequest:
    id: str
    pod: str
    serial: str
    request_type: str
    pod_m_type: PodMType
    user_type: UserType
    first_name: str
    last_name: str
    email: str
    fiscal_code: str
    contract_signed: bool
    product: str
    status: Status
    created_at: str
    updated_at: str
    group: str


@dataclass
class Chain2GateDevice:
    id: str
    m1: Optional[str]
    m2: Optional[str]
    m2_2: Optional[str]
    m2_3: Optional[str]
    m2_4: Optional[str]
    login_key: str
    du_name: str
    hw_version: str
    sw_version: str
    fw_version: str
    mac: str
    k1: str
    k2: str
    system_title: str
    created_at: str
    updated_at: str
    group: str
    type_name: str


@dataclass
class Customer:
    fiscal_code: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    user_type: Optional[UserType] = None
    group: Optional[str] = None
    admissibility_requests: List[AdmissibilityRequest] = None
    association_requests: List[AssociationRequest] = None
    disassociation_requests: List[DisassociationRequest] = None
    devices: List[Chain2GateDevice] = None

    def __post_init__(self):
        if self.admissibility_requests is None:
            self.admissibility_requests = []
        if self.association_requests is None:
            self.association_requests = []
        if self.disassociation_requests is None:
            self.disassociation_requests = []
        if self.devices is None:
            self.devices = []


class Chain2GateSDK:
    """Powerful Chain2Gate SDK for IoT energy monitoring device management"""
    
    def __init__(self, api_key: str, base_url: str = "https://chain2-api.chain2gate.it"):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"x-api-key": api_key, "Content-Type": "application/json"})

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Internal request handler with error management"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            data = response.json()
            
            if response.status_code >= 400:
                return {"error": True, "status_code": response.status_code, "message": data.get("message", "Unknown error")}
            
            return {"error": False, "data": data, "status_code": response.status_code}
        except Exception as e:
            return {"error": True, "status_code": 0, "message": str(e)}

    def _paginate(self, endpoint: str, limit: Optional[int] = None) -> Union[List[Dict], Dict]:
        """Handle pagination automatically"""
        all_items = []
        next_token = None
        
        while True:
            url = endpoint
            if next_token:
                url += f"{'&' if '?' in url else '?'}nextToken={next_token}"
            
            result = self._request("GET", url)
            if result["error"]:
                return result
            
            data = result["data"]
            items = data.get("items", data.get("result", []))
            if isinstance(items, list):
                all_items.extend(items)
            else:
                # Handle case where result is not a list
                break
            
            if limit and len(all_items) >= limit:
                return all_items[:limit]
            
            next_token = data.get("nextToken")
            if not next_token:
                break
        
        return all_items

    # === ADMISSIBILITY METHODS ===
    def get_admissibility_requests(self) -> Union[List[AdmissibilityRequest], Dict]:
        """Get all admissibility requests"""
        result = self._request("GET", "/admissibility")
        if result["error"]:
            return result
        
        # Handle different response structures
        items = result["data"].get("result", result["data"].get("items", []))
        return [AdmissibilityRequest(
            id=item["id"], pod=item.get("pod", ""), 
            status=Status(item["status"]) if item.get("status") else Status.PENDING,
            message=item.get("message", ""), fiscal_code=item.get("fiscalCode", ""),
            closed_at=item.get("closedAt"), created_at=item.get("createdAt", ""),
            updated_at=item.get("updatedAt", ""), group=item.get("group", "")
        ) for item in items]

    def get_admissibility_request(self, request_id: str) -> Union[AdmissibilityRequest, Dict]:
        """Get specific admissibility request"""
        result = self._request("GET", f"/admissibility/{request_id}")
        if result["error"]:
            return result
        
        item = result["data"]["result"]
        return AdmissibilityRequest(
            id=item["id"], pod=item["pod"], status=Status(item["status"]),
            message=item["message"], fiscal_code=item["fiscalCode"],
            closed_at=item["closedAt"], created_at=item["createdAt"],
            updated_at=item["updatedAt"], group=item["group"]
        )

    def create_admissibility_request(self, pod: str, fiscal_code: str) -> Union[AdmissibilityRequest, Dict]:
        """Create new admissibility request"""
        payload = {"pod": pod, "fiscalCode": fiscal_code}
        result = self._request("POST", "/admissibility", json=payload)
        if result["error"]:
            return result
        
        item = result["data"]["result"]
        return AdmissibilityRequest(
            id=item["id"], pod=item["pod"], status=Status(item["status"]),
            message=item["message"], fiscal_code=item["fiscalCode"],
            closed_at=item["closedAt"], created_at=item["createdAt"],
            updated_at=item["updatedAt"], group=item["group"]
        )

    # === ASSOCIATION METHODS ===
    def get_association_requests(self) -> Union[List[AssociationRequest], Dict]:
        """Get all association requests"""
        result = self._request("GET", "/associations")
        if result["error"]:
            return result
        
        # Handle different response structures
        items = result["data"].get("result", result["data"].get("items", []))
        return [AssociationRequest(
            id=item["id"], pod=item["pod"], serial=item.get("serial", ""),
            request_type=item.get("requestType", ""), 
            pod_m_type=PodMType(item["podMType"]) if item.get("podMType") else PodMType.M1,
            user_type=UserType(item["userType"]) if item.get("userType") else UserType.CONSUMER, 
            first_name=item.get("firstName", ""),
            last_name=item.get("lastName", ""), email=item.get("email", ""),
            contract_signed=item.get("contractSigned", False), product=item.get("product", ""),
            status=Status(item["status"]) if item.get("status") else Status.PENDING, 
            message=item.get("message", ""),
            fiscal_code=item.get("fiscalCode", ""), closed_at=item.get("closedAt"),
            created_at=item.get("createdAt", ""), updated_at=item.get("updatedAt", ""),
            group=item.get("group", "")
        ) for item in items]

    def get_association_request(self, request_id: str) -> Union[AssociationRequest, Dict]:
        """Get specific association request"""
        result = self._request("GET", f"/associations/{request_id}")
        if result["error"]:
            return result
        
        item = result["data"]["result"]
        return AssociationRequest(
            id=item["id"], pod=item["pod"], serial=item["serial"],
            request_type=item["requestType"], pod_m_type=PodMType(item["podMType"]),
            user_type=UserType(item["userType"]), first_name=item["firstName"],
            last_name=item["lastName"], email=item["email"],
            contract_signed=item["contractSigned"], product=item["product"],
            status=Status(item["status"]), message=item["message"],
            fiscal_code=item["fiscalCode"], closed_at=item["closedAt"],
            created_at=item["createdAt"], updated_at=item["updatedAt"],
            group=item["group"]
        )

    def create_association_request(self, pod: str, serial: str, pod_m_type: PodMType, 
                                 user_type: UserType, fiscal_code: str,
                                 first_name: str = None, last_name: str = None, 
                                 email: str = None) -> Union[AssociationRequest, Dict]:
        """Create new association request"""
        payload = {
            "pod": pod, "serial": serial, "podMType": pod_m_type.value,
            "userType": user_type.value, "fiscalCode": fiscal_code,
            "contractSigned": True
        }
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if email:
            payload["email"] = email
        
        result = self._request("POST", "/associations", json=payload)
        if result["error"]:
            return result
        
        item = result["data"]["result"]
        return AssociationRequest(
            id=item["id"], pod=item["pod"], serial=item["serial"],
            request_type=item["requestType"], pod_m_type=PodMType(item["podMType"]),
            user_type=UserType(item["userType"]), first_name=item.get("firstName", ""),
            last_name=item.get("lastName", ""), email=item.get("email", ""),
            contract_signed=item["contractSigned"], product=item["product"],
            status=Status(item["status"]), message=item.get("message", ""),
            fiscal_code=item["fiscalCode"], closed_at=item.get("closedAt"),
            created_at=item["createdAt"], updated_at=item["updatedAt"],
            group=item["group"]
        )

    # === DISASSOCIATION METHODS ===
    def get_disassociation_requests(self, limit: Optional[int] = None) -> Union[List[DisassociationRequest], Dict]:
        """Get all disassociation requests with pagination"""
        items = self._paginate("/disassociations", limit)
        if isinstance(items, dict) and items.get("error"):
            return items
        
        return [DisassociationRequest(
            id=item["id"], pod=item.get("pod", ""), serial=item.get("serial", ""),
            request_type=item.get("requestType", ""), 
            pod_m_type=PodMType(item["podMType"]) if item.get("podMType") else PodMType.M1,
            user_type=UserType(item["userType"]) if item.get("userType") else UserType.CONSUMER, 
            first_name=item.get("firstName", ""),
            last_name=item.get("lastName", ""), email=item.get("email", ""),
            fiscal_code=item.get("fiscalCode", ""), contract_signed=item.get("contractSigned", False),
            product=item.get("product", ""), 
            status=Status(item["status"]) if item.get("status") else Status.PENDING,
            created_at=item.get("createdAt", ""), updated_at=item.get("updatedAt", ""),
            group=item.get("group", "")
        ) for item in items]

    def get_disassociation_request(self, request_id: str) -> Union[DisassociationRequest, Dict]:
        """Get specific disassociation request"""
        result = self._request("GET", f"/disassociations/{request_id}")
        if result["error"]:
            return result
        
        item = result["data"]["result"]
        return DisassociationRequest(
            id=item["id"], pod=item["pod"], serial=item["serial"],
            request_type=item["requestType"], pod_m_type=PodMType(item["podMType"]),
            user_type=UserType(item["userType"]), first_name=item["firstName"],
            last_name=item["lastName"], email=item["email"],
            fiscal_code=item["fiscalCode"], contract_signed=item["contractSigned"],
            product=item["product"], status=Status(item["status"]),
            created_at=item["createdAt"], updated_at=item["updatedAt"],
            group=item["group"]
        )

    def create_disassociation_request(self, pod: str, serial: str, pod_m_type: PodMType,
                                    fiscal_code: str, user_type: UserType = None,
                                    first_name: str = None, last_name: str = None,
                                    email: str = None) -> Union[DisassociationRequest, Dict]:
        """Create new disassociation request"""
        payload = {
            "pod": pod, "serial": serial, "podMType": pod_m_type.value,
            "fiscalCode": fiscal_code, "contractSigned": True
        }
        if user_type:
            payload["userType"] = user_type.value
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if email:
            payload["email"] = email
        
        result = self._request("POST", "/disassociations", json=payload)
        if result["error"]:
            return result
        
        item = result["data"]["result"]
        return DisassociationRequest(
            id=item["id"], pod=item["pod"], serial=item["serial"],
            request_type=item["requestType"], pod_m_type=PodMType(item["podMType"]),
            user_type=UserType(item.get("userType", "CONSUMER")), 
            first_name=item.get("firstName", ""), last_name=item.get("lastName", ""),
            email=item.get("email", ""), fiscal_code=item["fiscalCode"],
            contract_signed=item["contractSigned"], product=item["product"],
            status=Status(item["status"]), created_at=item["createdAt"],
            updated_at=item["updatedAt"], group=item["group"]
        )

    # === DEVICE METHODS ===
    def get_devices(self, device_type: DeviceType = None, limit: Optional[int] = None) -> Union[List[Chain2GateDevice], Dict]:
        """Get Chain2Gate devices. If no device_type specified, gets all types."""
        if device_type:
            # Get specific device type
            endpoint = f"/chain2gate?type={device_type.value}"
            items = self._paginate(endpoint, limit)
            if isinstance(items, dict) and items.get("error"):
                return items
        else:
            # Get all device types by querying each type
            all_items = []
            for dtype in DeviceType:
                endpoint = f"/chain2gate?type={dtype.value}"
                items = self._paginate(endpoint, None)  # No limit per type
                if isinstance(items, dict) and items.get("error"):
                    continue  # Skip failed types
                all_items.extend(items)
                if limit and len(all_items) >= limit:
                    all_items = all_items[:limit]
                    break
            items = all_items
        
        return [Chain2GateDevice(
            id=item.get("id", ""), m1=item.get("m1"), m2=item.get("m2"), m2_2=item.get("m2_2"),
            m2_3=item.get("m2_3"), m2_4=item.get("m2_4"), login_key=item.get("loginKey", ""),
            du_name=item.get("duName", ""), hw_version=item.get("hwVersion", ""),
            sw_version=item.get("swVersion", ""), fw_version=item.get("fwVersion", ""),
            mac=item.get("mac", ""), k1=item.get("k1", ""), k2=item.get("k2", ""),
            system_title=item.get("systemTitle", ""), created_at=item.get("createdAt", ""),
            updated_at=item.get("updatedAt", ""), group=item.get("group", ""),
            type_name=item.get("__typename", "")
        ) for item in items]

    def get_devices_by_type(self, device_type: DeviceType, limit: Optional[int] = None) -> Union[List[Chain2GateDevice], Dict]:
        """Get devices by specific type (more reliable than getting all devices)"""
        return self.get_devices(device_type, limit)

    # === HELPER METHODS ===
    def get_customer_info(self, fiscal_code: str, skip_devices: bool = False) -> Union[Customer, Dict]:
        """Get complete customer information including all requests and devices"""
        customer = Customer(fiscal_code=fiscal_code)
        
        # Get admissibility requests
        admissibility = self.get_admissibility_requests()
        if isinstance(admissibility, dict) and admissibility.get("error"):
            return admissibility
        customer.admissibility_requests = [req for req in admissibility if req.fiscal_code == fiscal_code]
        
        # Get association requests
        associations = self.get_association_requests()
        if isinstance(associations, dict) and associations.get("error"):
            return associations
        customer.association_requests = [req for req in associations if req.fiscal_code == fiscal_code]
        
        # Get disassociation requests
        disassociations = self.get_disassociation_requests()
        if isinstance(disassociations, dict) and disassociations.get("error"):
            return disassociations
        customer.disassociation_requests = [req for req in disassociations if req.fiscal_code == fiscal_code]
        
        # Extract customer details from first available request
        for req in customer.association_requests + customer.disassociation_requests:
            if hasattr(req, 'first_name') and req.first_name:
                customer.first_name = req.first_name
                customer.last_name = req.last_name
                customer.email = req.email
                customer.user_type = req.user_type
                customer.group = req.group
                break
        
        # Get associated devices (optional, can be skipped if API has issues)
        if not skip_devices:
            devices = self.get_devices()
            if isinstance(devices, dict) and devices.get("error"):
                # Don't fail the whole request if devices endpoint fails
                customer.devices = []
                print(f"Warning: Could not fetch devices - {devices.get('message', 'Unknown error')}")
            else:
                # Find devices associated with customer's PODs
                customer_pods = set()
                for req in customer.association_requests:
                    customer_pods.add(req.pod)
                
                customer.devices = [device for device in devices 
                                  if any(pod in [device.m1, device.m2, device.m2_2, device.m2_3, device.m2_4] 
                                        for pod in customer_pods if pod)]
        
        return customer

    def debug_response(self, endpoint: str) -> Dict:
        """Debug helper to see raw API response structure"""
        return self._request("GET", endpoint)

    def associate_customer_device(self, fiscal_code: str, pod: str, serial: str, 
                                pod_m_type: PodMType, user_type: UserType,
                                first_name: str = None, last_name: str = None, 
                                email: str = None) -> Union[Dict, Dict]:
        """Complete flow: check admissibility then create association"""
        # First check/create admissibility
        admissibility = self.create_admissibility_request(pod, fiscal_code)
        if isinstance(admissibility, dict) and admissibility.get("error"):
            return admissibility
        
        # Create association request
        association = self.create_association_request(
            pod, serial, pod_m_type, user_type, fiscal_code, 
            first_name, last_name, email
        )
        
        return {
            "admissibility": admissibility,
            "association": association,
            "error": isinstance(association, dict) and association.get("error", False)
        }

    def get_device_by_serial(self, serial: str) -> Union[Chain2GateDevice, Dict, None]:
        """Find device by serial number"""
        devices = self.get_devices()
        if isinstance(devices, dict) and devices.get("error"):
            return devices
        
        for device in devices:
            if device.id == serial:
                return device
        return None