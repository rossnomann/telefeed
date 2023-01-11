#[tokio::main]
async fn main() {
    if let Err(err) = telefeed::app::run().await {
        log::error!("{err}");
    }
}
