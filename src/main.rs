fn main() {
    let data: Vec<usize> = (0..10_000).collect();
    let total: usize = data.iter().sum();
    println!("Total: {}", total);
}
