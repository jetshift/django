from dotenv import load_dotenv

load_dotenv()


async def pause_prefect_deployment(deployment_id, paused=True):
    import os
    import httpx
    from jetshift_core.js_logger import get_logger

    js_logger = get_logger()
    prefect_api_url = os.getenv("PREFECT_API_URL", "http://127.0.0.1:4200/api")
    url = f"{prefect_api_url}/deployments/{deployment_id}"

    headers = {
        "Content-Type": "application/json"
    }

    api_key = os.getenv("PREFECT_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "paused": paused
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, json=payload, headers=headers)

        if response.status_code == 204:
            action = "paused" if paused else "unpaused"
            js_logger.info(f"Deployment {deployment_id} {action} successfully.")
        else:
            js_logger.error(
                f"Failed to update deployment: {response.status_code} - {response.text}"
            )
    except httpx.RequestError as e:
        js_logger.exception(f"HTTP request error while updating deployment: {e}")
    except Exception as e:
        js_logger.exception(f"Unexpected error: {e}")
