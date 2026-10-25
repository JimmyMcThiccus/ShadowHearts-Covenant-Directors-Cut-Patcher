use sh2_script::{disasm::scan_calls, image::ScriptImage};
use std::collections::BTreeMap;
// usage: msccalls <dir>  -> prints "ex.sub count files" and parse failures
fn main() {
    let dir = std::env::args().nth(1).unwrap();
    let mut calls: BTreeMap<(u8, u8), (usize, Vec<String>)> = BTreeMap::new();
    let (mut ok, mut bad) = (0, 0);
    for e in std::fs::read_dir(&dir).unwrap() {
        let p = e.unwrap().path();
        if p.extension().map(|x| x != "MSC").unwrap_or(true) { continue; }
        let name = p.file_stem().unwrap().to_string_lossy().to_string();
        let b = std::fs::read(&p).unwrap();
        match ScriptImage::parse(&b) {
            Ok(img) => { ok += 1;
                for c in scan_calls(&img) { if c.ex == 0xc2 && (c.sub == 0x72 || c.sub == 0x73 || c.sub == 0x0d) { eprintln!("BTL {name} {:02x} {:?}", c.sub, c.args); } let ent = calls.entry((c.ex, c.sub)).or_default(); ent.0 += 1; if !ent.1.contains(&name) { ent.1.push(name.clone()); } } }
            Err(err) => { bad += 1; eprintln!("parse fail {name}: {err:?}"); }
        }
    }
    println!("# parsed {ok}, failed {bad}");
    for ((ex, sub), (n, files)) in calls { println!("{ex:02x}.{sub:02x} {n} {}", files.join(",")); }
}
