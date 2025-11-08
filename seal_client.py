"""SEAL API client for fetching intervention plans."""

import requests
from typing import Optional, Dict, Any
import json
from tilli_prompts.schemas import InterventionRequest, CurriculumRequest


class SEALAPIClient:
    """Client for interacting with SEAL API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize SEAL API client.

        Args:
            base_url: Base URL of the SEAL API (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = 30  # seconds

    def health_check(self) -> bool:
        """Check if SEAL API is healthy and accessible."""
        try:
            response = requests.get(
                f"{self.base_url}/health", timeout=10  # Increased timeout
            )
            # Accept 200 status even if status is "degraded" - service is still accessible
            if response.status_code == 200:
                return True
            return False
        except requests.exceptions.Timeout:
            return False
        except requests.exceptions.ConnectionError:
            return False
        except Exception as e:
            # Log the exception for debugging but don't raise
            return False

    def generate_intervention(
        self, request: InterventionRequest, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an intervention plan from SEAL API.

        Args:
            request: InterventionRequest object with scores and metadata
            timeout: Request timeout in seconds (default: self.timeout)

        Returns:
            Dictionary containing the intervention plan

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        url = f"{self.base_url}/score"
        timeout = timeout or self.timeout

        # Convert Pydantic model to dict
        payload = request.model_dump()

        try:
            response = requests.post(
                url, json=payload, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise requests.RequestException(
                f"Request to {url} timed out after {timeout} seconds"
            )
        except requests.exceptions.HTTPError as e:
            error_msg = f"API error: {e.response.status_code}"
            try:
                error_detail = e.response.json().get("detail", "")
                error_msg += f" - {error_detail}"
            except Exception:
                pass
            raise requests.RequestException(error_msg)
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(f"Failed to connect to SEAL API: {str(e)}")

    def generate_curriculum(
        self, request: CurriculumRequest, timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a curriculum plan from SEAL API.

        Args:
            request: CurriculumRequest object with grade level, skill areas, and score
            timeout: Request timeout in seconds (default: self.timeout)

        Returns:
            Dictionary containing the curriculum plan

        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        url = f"{self.base_url}/curriculum"
        timeout = timeout or self.timeout

        # Convert Pydantic model to dict
        payload = request.model_dump()

        try:
            response = requests.post(
                url, json=payload, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            raise requests.RequestException(
                f"Request to {url} timed out after {timeout} seconds"
            )
        except requests.exceptions.HTTPError as e:
            error_msg = f"API error: {e.response.status_code}"
            try:
                error_detail = e.response.json().get("detail", "")
                error_msg += f" - {error_detail}"
            except Exception:
                pass
            raise requests.RequestException(error_msg)
        except requests.exceptions.RequestException as e:
            raise requests.RequestException(f"Failed to connect to SEAL API: {str(e)}")

    def generate_intervention_from_dict(
        self, data: Dict[str, Any], timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate intervention plan from dictionary (convenience method).

        Args:
            data: Dictionary with scores and metadata
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing the intervention plan
        """
        request = InterventionRequest(**data)
        return self.generate_intervention(request, timeout)

    def generate_curriculum_from_dict(
        self, data: Dict[str, Any], timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate curriculum plan from dictionary (convenience method).

        Args:
            data: Dictionary with grade_level, skill_areas, and score
            timeout: Request timeout in seconds

        Returns:
            Dictionary containing the curriculum plan
        """
        request = CurriculumRequest(**data)
        return self.generate_curriculum(request, timeout)



