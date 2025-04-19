fn fib(n: u32) -> u32 {
    if n < 2 {
        n
    } else {
        fib(n - 1) + fib(n - 2)
    }
}

fn main() {
    for i in 0..35 {
        println!("fib({}) = {}", i, fib(i));
    }
}
