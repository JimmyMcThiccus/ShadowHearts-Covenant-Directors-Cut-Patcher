//! LSD `PCMS` payload codec: stereo SPU-ADPCM, L/R chunks of 0x800 bytes, 16-byte blocks of 28 samples.
//! usage: pcmscodec decode IN.pcms OUT.raw        (s16le stereo interleaved)
//!        pcmscodec encode IN.raw OUT.pcms BYTES   (BYTES = payload size to produce; tail padded with zero blocks)
use std::{env, fs};

const COEF: [(i32, i32); 5] = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)];
const IL: usize = 0x800;

fn decode_block(b: &[u8], h: &mut (i32, i32), out: &mut Vec<i16>) {
    let shift = (b[0] & 15) as i32;
    let (c1, c2) = COEF[((b[0] >> 4) as usize).min(4)];
    for i in 0..28 {
        let byte = b[2 + i / 2];
        let nib = if i & 1 == 0 { byte & 15 } else { byte >> 4 } as i32;
        let nib = if nib >= 8 { nib - 16 } else { nib };
        let s = if shift <= 12 { (nib << 12) >> shift } else { 0 };
        let v = (s + ((h.0 * c1 + h.1 * c2 + 32) >> 6)).clamp(-32768, 32767);
        h.1 = h.0;
        h.0 = v;
        out.push(v as i16);
    }
}

/// Encode 28 samples; returns the block and updates the decoder history exactly as the SPU would.
fn encode_block(x: &[i32; 28], h: &mut (i32, i32), flag: u8) -> [u8; 16] {
    let mut best: Option<(i64, [u8; 16], (i32, i32))> = None;
    for f in 0..5 {
        let (c1, c2) = COEF[f];
        // shift estimate from the open-loop residual
        let (mut p1, mut p2) = (h.0, h.1);
        let mut peak = 0i32;
        for &s in x.iter() {
            let r = s - ((p1 * c1 + p2 * c2 + 32) >> 6);
            peak = peak.max(r.abs());
            p2 = p1;
            p1 = s;
        }
        let mut sh0 = 12i32;
        while sh0 > 0 && (peak > (7 << (12 - sh0)) ) { sh0 -= 1; }
        for shift in [sh0, sh0 - 1, sh0 + 1] {
            if !(0..=12).contains(&shift) { continue; }
            let mut blk = [0u8; 16];
            blk[0] = ((f as u8) << 4) | shift as u8;
            blk[1] = flag;
            let mut st = *h;
            let mut err = 0i64;
            for i in 0..28 {
                let pred = (st.0 * c1 + st.1 * c2 + 32) >> 6;
                let r = x[i] - pred;
                let step = 1i32 << (12 - shift);
                let q = ((r + step / 2).div_euclid(step)).clamp(-8, 7);
                let v = (((q << 12) >> shift) + pred).clamp(-32768, 32767);
                st.1 = st.0;
                st.0 = v;
                let d = (x[i] - v) as i64;
                err += d * d;
                let nib = (q & 15) as u8;
                blk[2 + i / 2] |= if i & 1 == 0 { nib } else { nib << 4 };
            }
            if best.as_ref().map_or(true, |b| err < b.0) { best = Some((err, blk, st)); }
        }
    }
    let (_, blk, st) = best.unwrap();
    *h = st;
    blk
}

fn main() {
    let a: Vec<String> = env::args().collect();
    match a[1].as_str() {
        "decode" => {
            let d = fs::read(&a[2]).unwrap();
            let rounds = d.len() / (2 * IL);
            let (mut l, mut r) = (Vec::new(), Vec::new());
            let (mut hl, mut hr) = ((0, 0), (0, 0));
            for k in 0..rounds {
                let base = k * 2 * IL;
                for b in (0..IL).step_by(16) { decode_block(&d[base + b..base + b + 16], &mut hl, &mut l); }
                for b in (0..IL).step_by(16) { decode_block(&d[base + IL + b..base + IL + b + 16], &mut hr, &mut r); }
            }
            let mut out = Vec::with_capacity(l.len() * 4);
            for i in 0..l.len() { out.extend_from_slice(&l[i].to_le_bytes()); out.extend_from_slice(&r[i].to_le_bytes()); }
            fs::write(&a[3], out).unwrap();
            eprintln!("decoded {} frames ({:.2} s)", l.len(), l.len() as f64 / 48000.0);
        }
        "encode" => {
            let d = fs::read(&a[2]).unwrap();
            let total: usize = a[4].parse().unwrap();
            assert!(total % (2 * IL) == 0);
            let frames = d.len() / 4;
            let ch = |c: usize| -> Vec<i32> { (0..frames).map(|i| i16::from_le_bytes([d[i * 4 + c * 2], d[i * 4 + c * 2 + 1]]) as i32).collect() };
            let (l, r) = (ch(0), ch(1));
            let per = total / 2; // bytes per channel
            let nblk = per / 16;
            let audio_blk = (frames + 27) / 28;
            assert!(audio_blk <= nblk, "audio {} blocks > room {}", audio_blk, nblk);
            let enc = |s: &Vec<i32>| -> Vec<u8> {
                let mut h = (0, 0);
                let mut out = vec![0u8; per];
                for b in 0..audio_blk {
                    let mut x = [0i32; 28];
                    for i in 0..28 { x[i] = *s.get(b * 28 + i).unwrap_or(&0); }
                    out[b * 16..b * 16 + 16].copy_from_slice(&encode_block(&x, &mut h, 2));
                }
                out
            };
            let (el, er) = (enc(&l), enc(&r));
            let mut out = Vec::with_capacity(total);
            for k in 0..per / IL { out.extend_from_slice(&el[k * IL..k * IL + IL]); out.extend_from_slice(&er[k * IL..k * IL + IL]); }
            fs::write(&a[3], out).unwrap();
            eprintln!("encoded {} frames into {} blocks/channel ({} padding)", frames, nblk, nblk - audio_blk);
        }
        _ => panic!("decode|encode"),
    }
}
