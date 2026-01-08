import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Depends, Header
from pydantic import BaseModel
from backend.utils.logger import logger
from backend.core.supabase_manager import SupabaseManager

router = APIRouter()
session_manager = SupabaseManager()

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
price_id = os.getenv("STRIPE_PRICE_ID", "price_placeholder")

class CheckoutRequest(BaseModel):
    userId: str
    email: str

@router.post("/create-checkout-session")
async def create_checkout_session(req: CheckoutRequest):
    try:
        domain_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        
        # Create or retrieve customer (simplified)
        # In a real app, we would search stripe by email first or store stripe_customer_id in DB
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=domain_url + '/settings?success=true',
            cancel_url=domain_url + '/settings?canceled=true',
            customer_email=req.email,
            client_reference_id=req.userId,
            metadata={
                'user_id': req.userId
            }
        )
        return {"id": checkout_session.id, "url": checkout_session.url}
    except Exception as e:
        logger.error(f"Stripe Checkout Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, webhook_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        await handle_checkout_completed(session)
    
    # Handle other events likely (invoice.payment_succeeded, customer.subscription.deleted)
    
    return {"status": "success"}

async def handle_checkout_completed(session):
    user_id = session.get("client_reference_id")
    customer_id = session.get("customer")
    
    if user_id:
        logger.info(f"Upgrade User {user_id} to PRO")
        # Update user profile in Supabase
        # We need raw SQL or a specific method in session_manager
        try:
            session_manager.supabase.table("profiles").update({
                "stripe_customer_id": customer_id,
                "subscription_tier": "pro",
                "subscription_status": "active"
            }).eq("id", user_id).execute()
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
