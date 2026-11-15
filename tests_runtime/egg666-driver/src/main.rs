use egg::{EGraph, Id, SymbolLang};
use std::io::{self, Read};

fn evaluate(input: &str) -> Result<String, &'static str> {
    if input.len() > 4096 || !input.bytes().all(|b| b.is_ascii_digit() || b == b' ' || b == b'\n') {
        return Err("bounded integers required");
    }
    let mut tokens = input.split_whitespace();
    let mut next = || tokens.next().ok_or("missing integer")?.parse::<usize>().map_err(|_| "invalid integer");
    let n = next()?;
    if !(1..=16).contains(&n) { return Err("node limit"); }
    let mut graph = EGraph::<SymbolLang, ()>::default();
    let mut ids: Vec<Id> = Vec::new();
    for i in 0..n {
        let op = next()?;
        let arity = next()?;
        if op > 7 || arity > 2 { return Err("operator or arity limit"); }
        let mut children = Vec::new();
        for _ in 0..arity {
            let child = next()?;
            if child >= i { return Err("acyclic prior child required"); }
            children.push(ids[child]);
        }
        ids.push(graph.add(SymbolLang::new(format!("synthetic_op_{op}"), children)));
    }
    let m = next()?;
    if m > 16 { return Err("equality limit"); }
    for _ in 0..m {
        let a = next()?;
        let b = next()?;
        if a >= n || b >= n { return Err("equality index limit"); }
        graph.union(ids[a], ids[b]);
    }
    drop(next);
    if tokens.next().is_some() { return Err("extra integer"); }
    graph.rebuild();
    let mut output = format!("{n} {}\n", graph.number_of_classes());
    for i in 0..n {
        for j in 0..n {
            output.push(if graph.find(ids[i]) == graph.find(ids[j]) { '1' } else { '0' });
        }
    }
    output.push('\n');
    Ok(output)
}

fn main() {
    let mut input = String::new();
    if io::stdin().take(4097).read_to_string(&mut input).is_err() {
        eprintln!("invalid input"); std::process::exit(2);
    }
    match evaluate(&input) {
        Ok(output) => print!("{output}"),
        Err(_) => { eprintln!("invalid bounded congruence input"); std::process::exit(2); }
    }
}
