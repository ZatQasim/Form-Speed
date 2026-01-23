mod network_monitor;
mod router_client;
mod arn_module;
mod speed_sharing;
mod security_agent;

use network_monitor::collect_metrics;
use router_client::request_route;
use arn_module::evaluate_context;
use speed_sharing::sync_bandwidth;
use security_agent::start_security_agent;

fn main() {
    start_security_agent();

    loop {
        let metrics = collect_metrics();
        let context = evaluate_context(&metrics);
        let route = request_route(&context);
        sync_bandwidth(&metrics);

        println!("Active route: {}", route);
        std::thread::sleep(std::time::Duration::from_secs(5));
    }
}