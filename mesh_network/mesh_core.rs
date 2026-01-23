use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

#[derive(Clone, Debug)]
pub struct Node {
    pub id: String,
    pub ip: String,
    pub latency_ms: u32,
}

pub struct MeshNetwork {
    pub nodes: Arc<Mutex<HashMap<String, Node>>>,
}

impl MeshNetwork {
    pub fn new() -> MeshNetwork {
        MeshNetwork {
            nodes: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn add_node(&self, node: Node) {
        self.nodes.lock().unwrap().insert(node.id.clone(), node);
    }

    pub fn remove_node(&self, node_id: &str) {
        self.nodes.lock().unwrap().remove(node_id);
    }

    pub fn select_best_node(&self) -> Option<Node> {
        let nodes = self.nodes.lock().unwrap();
        nodes.values().min_by_key(|n| n.latency_ms).cloned()
    }

    pub fn monitor_nodes(&self) {
        let nodes_clone = self.nodes.clone();
        thread::spawn(move || loop {
            {
                let mut nodes = nodes_clone.lock().unwrap();
                for (_, node) in nodes.iter_mut() {
                    // Simulate latency measurement
                    node.latency_ms = node.latency_ms.saturating_add(1) % 100;
                }
            }
            thread::sleep(Duration::from_secs(5));
        });
    }
}