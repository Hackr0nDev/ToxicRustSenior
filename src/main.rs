fn main() {
    let mut data = Vec::new();
    for i in 0..10_000 {
        data.push(i.to_string().clone());
    }

    let total: usize = data
        .iter()
        .map(|s| s.parse::<usize>().unwrap())
        .fold(0, |acc, x| acc + x);

    println!("Total: {}", total);
}
