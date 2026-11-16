use oxigraph::model::{GraphName, NamedNode, Quad, Term};
use oxigraph::sparql::{QueryResults, SparqlEvaluator};
use oxigraph::store::Store;
use std::io::{self, Read};

const EDGE: &str = "urn:verdugo:synthetic-edge";
const PREFIX: &str = "urn:verdugo:synthetic-node:";
const QUERY: &str = "SELECT DISTINCT ?source ?target WHERE { ?source <urn:verdugo:synthetic-edge>+ ?target }";

fn quad(a: usize, b: usize) -> Result<Quad, Box<dyn std::error::Error>> {
    Ok(Quad::new(NamedNode::new(format!("{PREFIX}{a}"))?, NamedNode::new(EDGE)?,
                 NamedNode::new(format!("{PREFIX}{b}"))?, GraphName::DefaultGraph))
}
fn index(term: Option<&Term>) -> Result<usize, Box<dyn std::error::Error>> {
    let Some(Term::NamedNode(node)) = term else { return Err("unexpected term".into()); };
    let i: usize = node.as_str().strip_prefix(PREFIX).ok_or("unexpected namespace")?.parse()?;
    if i >= 8 { return Err("unexpected node".into()); }
    Ok(i)
}
fn paths(store: &Store) -> Result<String, Box<dyn std::error::Error>> {
    let mut bits = [b'0'; 64];
    let QueryResults::Solutions(solutions) = SparqlEvaluator::new().parse_query(QUERY)?.on_store(store).execute()? else {
        return Err("unexpected query result".into());
    };
    for solution in solutions {
        let row = solution?;
        let (a, b) = (index(row.get("source"))?, index(row.get("target"))?);
        if bits[a*8+b] != b'0' { return Err("unexpected duplicate path".into()); }
        bits[a*8+b] = b'1';
    }
    Ok(String::from_utf8(bits.to_vec())?)
}
fn evaluate(input: &str) -> Result<String, Box<dyn std::error::Error>> {
    if input.len()>4096 || !input.bytes().all(|b|b.is_ascii_digit() || b==b' ' || b==b'\n') {
        return Err("bounded integers required".into());
    }
    let mut values = input.split_whitespace();
    let mut next = || -> Result<usize, Box<dyn std::error::Error>> { Ok(values.next().ok_or("missing integer")?.parse()?) };
    let n = next()?;
    if n>32 { return Err("edge limit".into()); }
    let store = Store::new()?;
    for _ in 0..n {
        let (a,b)=(next()?,next()?);
        if a>=8 || b>=8 { return Err("node limit".into()); }
        store.insert(quad(a,b)?)?;
    }
    let before_count=store.len()?;
    let before=paths(&store)?;
    let m=next()?;
    if m>8 { return Err("remove limit".into()); }
    for _ in 0..m {
        let (a,b)=(next()?,next()?);
        if a>=8 || b>=8 { return Err("node limit".into()); }
        store.remove(&quad(a,b)?)?;
    }
    drop(next);
    if values.next().is_some() { return Err("extra integer".into()); }
    let after_count=store.len()?;
    let after=paths(&store)?;
    Ok(format!("{before_count} {after_count}\n{before}\n{after}\n"))
}
fn main() {
    let mut input=String::new();
    if io::stdin().take(4097).read_to_string(&mut input).is_err() {
        eprintln!("invalid input");std::process::exit(2);
    }
    match evaluate(&input) {
        Ok(out)=>print!("{out}"),
        Err(_)=>{eprintln!("invalid bounded graph input");std::process::exit(2);}
    }
}
