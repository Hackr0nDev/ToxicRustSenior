fn main() {
    // 0 1 1 2 3 5 8 13..

    let n = 186;
    let mut num: u128 = 1;
    let mut num1: u128 = 1;

    for _i in 2..n {
        let num2: u128 = num1;
        num1 = num;
        num = num1 + num2;
    }
    println!("n: {n} \nfib: {num}")
}
