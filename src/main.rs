use std::cmp::Ordering;
use std::io;

use rand::Rng;

fn main() {
    println!("Gues the number:");
    let secret_num = rand::thread_rng().gen_range(1..=100);

    loop {
        let mut guess = String::new();
        io::stdin()
            .read_line(&mut guess)
            .expect("Failed to read line");

        let guess: u32 = match guess.trim().parse() {
            Ok(num) => num,
            Err(_) => continue,
        };
        // let guess: i32 = guess.trim().parse().expect("errorka");

        match guess.cmp(&secret_num) {
            Ordering::Less => println!("Too small"),
            Ordering::Equal => {
                println!("You win!");
                break;
            }
            Ordering::Greater => println!("Too big"),
        }
    }
}
