import logging

import azure.functions as func

from functions.telegram_webhook import main as telegram_webhook_handler

app = func.FunctionApp()


@app.route(route="telegram_webhook", auth_level=func.AuthLevel.ANONYMOUS)
async def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    """
    Route handler for telegram webhook
    """
    logging.info("Telegram webhook triggered")

    try:
        # Call our telegram webhook handler
        return await telegram_webhook_handler(req)

    except Exception as e:
        logging.error(f"Error in telegram webhook: {str(e)}", exc_info=True)
        return func.HttpResponse("Internal server error", status_code=500)