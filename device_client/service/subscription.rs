use serde::{Deserialize, Serialize};
use std::fs;
use std::env;
use stripe::{Client, Subscription, SubscriptionItemParams, CreateSubscription, Customer};

#[derive(Deserialize, Serialize)]
struct ProUsers {
    users: Vec<String>,
}

pub struct SubscriptionManager {
    stripe_key: String,
    username: String,
}

impl SubscriptionManager {
    pub fn new(username: &str) -> Self {
        let stripe_key = env::var("STRIPE_KEY").expect("STRIPE_KEY must be set");
        SubscriptionManager {
            stripe_key,
            username: username.to_string(),
        }
    }

    // Check if the user is listed in pro.json
    fn is_pro_local(&self) -> bool {
        let data = fs::read_to_string("service/pro.json").unwrap_or_else(|_| "{\"users\":[]}".to_string());
        let pro: ProUsers = serde_json::from_str(&data).unwrap_or(ProUsers { users: vec![] });
        pro.users.contains(&self.username)
    }

    // Stripe subscription check
    async fn is_pro_stripe(&self) -> bool {
        let client = Client::new(&self.stripe_key);

        // Fetch customer by email/username (example: assuming username is email)
        let customers = stripe::Customer::list(&client, stripe::ListCustomers::new().email(&self.username))
            .await
            .unwrap();

        if let Some(customer) = customers.data.first() {
            let subscriptions = stripe::Subscription::list(
                &client,
                stripe::ListSubscriptions::new().customer(&customer.id),
            )
            .await
            .unwrap();

            return subscriptions.data.iter().any(|sub| sub.status == stripe::SubscriptionStatus::Active);
        }

        false
    }

    // Grant Pro benefits
    pub async fn grant_access(&self) {
        if self.is_pro_local() || self.is_pro_stripe().await {
            println!("{} is a Pro user! Unlocking premium features...", self.username);
            // Unlock features here, e.g.:
            // VPN, mesh, ARN, speed sharing, etc.
        } else {
            println!("{} is not a Pro user. Enable trial or limited features.", self.username);
        }
    }

    // Create a new Stripe subscription for the user
    pub async fn create_subscription(&self, customer_email: &str) {
        let client = Client::new(&self.stripe_key);

        // Create customer if not exists
        let customer = Customer::create(&client, stripe::CreateCustomer {
            email: Some(customer_email),
            ..Default::default()
        })
        .await
        .unwrap();

        // Create subscription
        let subscription = Subscription::create(&client, CreateSubscription {
            customer: customer.id.clone(),
            items: vec![SubscriptionItemParams {
                price: Some("price_5usd_month".to_string()), // Your Stripe Price ID
                ..Default::default()
            }],
            ..Default::default()
        })
        .await
        .unwrap();

        println!("Subscription created for {} with ID: {}", customer_email, subscription.id);
    }
}

// Example usage
#[tokio::main]
async fn main() {
    let username = "Abdi123"; // Replace with logged-in username
    let sub_manager = SubscriptionManager::new(username);

    // Grant access based on pro.json or Stripe
    sub_manager.grant_access().await;

    // Optional: Create subscription via Stripe
    // sub_manager.create_subscription("user_email@example.com").await;
}