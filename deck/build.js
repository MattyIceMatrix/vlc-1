const pptxgen = require('pptxgenjs');
const p = new pptxgen();
p.layout = 'LAYOUT_WIDE';               // 13.3 x 7.5
const W = 13.3, H = 7.5;

const BG   = '101826', PANEL = '1B2942', LINE = '2C3F61';
const TXT  = 'E8EEF7', MUT = '93A7C4';
const AMB  = 'E8A33D', MINT = '4FD1A5', RED = 'E06C6C';
const HEAD = 'Cambria', BODY = 'Calibri';

p.defineSlideMaster({ title:'DARK', background:{ color: BG } });
p.defineSlideMaster({ title:'LIGHT', background:{ color: 'FFFFFF' } });

const sh = () => ({ type:'outer', color:'000000', blur:12, offset:3, angle:90, opacity:0.35 });

function dark(){ return p.addSlide({ masterName:'DARK' }); }
function light(){ return p.addSlide({ masterName:'LIGHT' }); }

function title(s, t, sub, dk){
  s.addText(t, { x:0.7, y:0.5, w:W-1.4, h:0.9, fontSize:38, bold:true, fontFace:HEAD,
                 color: dk?TXT:'101826', isTextBox:true, margin:0 });
  if (sub) s.addText(sub, { x:0.7, y:1.35, w:W-1.4, h:0.5, fontSize:16, italic:true,
                 color: dk?MUT:'5A6B85', fontFace:BODY, isTextBox:true, margin:0 });
}
function foot(s, txt){
  s.addText(txt, { x:0.7, y:H-0.55, w:W-1.4, h:0.35, fontSize:10, color: MUT,
                   fontFace:BODY, isTextBox:true, margin:0 });
}
// a card: icon circle + header + body
function card(s, x, y, w, h, col, glyph, head, body, dk){
  s.addShape(p.ShapeType.roundRect, { x, y, w, h, fill:{ color: dk?PANEL:'F4F7FC' },
    rectRadius:0.12, line:{ color: dk?LINE:'DCE4F0', width:1 }, shadow: sh() });
  s.addShape(p.ShapeType.ellipse, { x:x+0.3, y:y+0.3, w:0.62, h:0.62, fill:{ color: col } });
  s.addText(glyph, { x:x+0.3, y:y+0.3, w:0.62, h:0.62, fontSize:22, bold:true, align:'center',
    valign:'middle', color:'101826', fontFace:HEAD, isTextBox:true, margin:0 });
  s.addText(head, { x:x+1.05, y:y+0.25, w:w-1.3, h:0.72, fontSize:16, bold:true,
    color: dk?TXT:'101826', fontFace:HEAD, isTextBox:true, margin:0, valign:'middle' });
  s.addText(body, { x:x+0.32, y:y+1.05, w:w-0.64, h:h-1.35, fontSize:13, color: dk?MUT:'44556F',
    fontFace:BODY, isTextBox:true, margin:0, valign:'top', lineSpacingMultiple:1.15 });
}
function stat(s, x, y, w, num, label, col, dk){
  s.addText(num, { x, y, w, h:1.0, fontSize:56, bold:true, color:col, fontFace:HEAD,
    isTextBox:true, margin:0, align:'left' });
  s.addText(label, { x, y:y+1.02, w, h:0.9, fontSize:13, color: dk?MUT:'44556F',
    fontFace:BODY, isTextBox:true, margin:0, valign:'top', lineSpacingMultiple:1.1 });
}

/* ---------------------------------------------------------------- 1 title */
{ const s = dark();
  s.addShape(p.ShapeType.ellipse, { x:W-3.6, y:-1.4, w:5.0, h:5.0, fill:{ color:'16233A' } });
  s.addShape(p.ShapeType.ellipse, { x:W-2.4, y:-0.6, w:2.6, h:2.6, fill:{ color:'1E3050' } });
  s.addText('VLC-1', { x:0.8, y:1.5, w:6, h:0.5, fontSize:14, bold:true, charSpacing:4,
    color:AMB, fontFace:BODY, isTextBox:true, margin:0 });
  s.addText('How do you know\nthis log is all of it?', { x:0.8, y:2.05, w:8.6, h:2.0,
    fontSize:46, bold:true, color:TXT, fontFace:HEAD, isTextBox:true, margin:0,
    lineSpacingMultiple:1.05 });
  s.addText('Verifiable completeness for AI system logs — a specification, a conformance checker, '
          + 'a machine-checked proof, and a record the audited process cannot write.',
    { x:0.8, y:4.2, w:9.2, h:1.0, fontSize:16, color:MUT, fontFace:BODY, isTextBox:true,
      margin:0, lineSpacingMultiple:1.2 });
  s.addText('Matthew Moore  ·  moorematthew131@gmail.com  ·  2026', { x:0.8, y:H-1.1, w:8, h:0.4,
    fontSize:12, color:'6F87AA', fontFace:BODY, isTextBox:true, margin:0 });
  s.addNotes('Open on the question, not on the product. Every buyer already believes their logs '
    + 'are tamper-evident. Nobody has been asked the completeness question yet, and that is the '
    + 'whole opening.');
}

/* ------------------------------------------------------- 2 the gap in one slide */
{ const s = light();
  title(s, 'Every AI logging standard says what to log', 'None of them says how you know the log is all of it.', false);
  stat(s, 0.75, 2.2, 3.4, '0', 'requirements in prEN 18229-1 addressing dropped events, gaps, or completeness', AMB, false);
  stat(s, 4.55, 2.2, 3.4, '0', 'requirements in ISO/IEC FDIS 24970 addressing loss accounting or guaranteed capture', AMB, false);
  stat(s, 8.35, 2.2, 4.2, 'Dec 2027', 'when EU AI Act Articles 9–15 apply to every high-risk deployer', '101826', false);
  s.addShape(p.ShapeType.roundRect, { x:0.75, y:4.9, w:W-1.5, h:1.5, fill:{ color:'FDF3E3' },
    rectRadius:0.1, line:{ color:'F0D7A8', width:1 } });
  s.addText('An evidence export covering a two-hour outage — during which the logging path '
    + 'discarded every record — is byte-for-byte indistinguishable from an export covering a '
    + 'quiet afternoon. Both verify. Both look complete.',
    { x:1.05, y:5.15, w:W-2.1, h:1.0, fontSize:16, color:'6B4A12', fontFace:BODY,
      isTextBox:true, margin:0, lineSpacingMultiple:1.2 });
  foot(s, 'Sources: prEN 18229-1 public-enquiry draft; ISO/IEC CD 24970; Regulation (EU) 2024/1689 Arts. 12, 19.');
  s.addNotes('The two zeros are the slide. Do not rush past them. Then read the amber box aloud.');
}

/* ---------------------------------------------------- 3 integrity is not completeness */
{ const s = dark();
  title(s, 'Tamper-evidence answers a different question', 'and the industry stopped once it had the answer to that one.', true);
  card(s, 0.75, 2.25, 5.7, 3.95, MINT, '✓', 'What a hash chain proves',
    'The records you were GIVEN were not altered, reordered, inserted or removed.\n\n'
  + 'This is solved work. Certificate Transparency, signed syslog, WORM storage, '
  + 'blockchain anchoring — all of it lands here, and lands well.', true);
  card(s, 6.85, 2.25, 5.7, 3.95, AMB, '?', 'What it says about the rest',
    'Nothing.\n\nA valid chain over 800 records is equally valid whether 800 or 8,000 '
  + 'were produced. Bounded buffers discard under load — preferentially during '
  + 'incidents, which are exactly the intervals the log exists to cover.', true);
  foot(s, 'VLC-1 §4, §5 · proofs/sentinel_completeness.v : integrity_alone_cannot_see_a_silent_drop');
  s.addNotes('If they push back here, the theorem name is the answer: two sessions, one lossy and '
    + 'one quiet, deliver identical record sets. Every function of the delivered set agrees.');
}

/* ------------------------------------------- 4 the blind spot nobody has named */
{ const s = light();
  title(s, 'The second blind spot has no symptom at all', 'An event at a source nobody instrumented produces no record, so it loses nothing, so no gap appears.', false);
  s.addShape(p.ShapeType.roundRect, { x:0.75, y:2.25, w:5.7, h:3.95, fill:{ color:'F4F7FC' },
    rectRadius:0.12, line:{ color:'DCE4F0', width:1 }, shadow: sh() });
  s.addText('L2-looks-complete.jsonl', { x:1.05, y:2.5, w:5.1, h:0.4, fontSize:15, bold:true,
    fontFace:'Courier New', color:'101826', isTextBox:true, margin:0 });
  s.addText([
    { text:'chain valid · end marker present', options:{ bullet:true, breakLine:true } },
    { text:'60 delivered  +  0 declared lost  =  60 produced', options:{ bullet:true, breakLine:true } },
    { text:'identity closes exactly', options:{ bullet:true, breakLine:true } },
    { text:'clean by every check performed today', options:{ bullet:true } },
  ], { x:1.05, y:3.0, w:5.1, h:1.6, fontSize:13.5, color:'44556F', fontFace:BODY,
       isTextBox:true, margin:0, paraSpaceAfter:6 });
  s.addText('…and 58 inferences that session went through a route the proxy was never '
    + 'instrumented for.', { x:1.05, y:5.15, w:5.1, h:0.8, fontSize:14, bold:true, color:'A8341F',
      fontFace:BODY, isTextBox:true, margin:0 });

  s.addShape(p.ShapeType.roundRect, { x:6.85, y:2.25, w:5.7, h:3.95, fill:{ color:'ECFAF4' },
    rectRadius:0.12, line:{ color:'B6E5D3', width:1 }, shadow: sh() });
  s.addText('L3-coverage.jsonl', { x:7.15, y:2.5, w:5.1, h:0.4, fontSize:15, bold:true,
    fontFace:'Courier New', color:'101826', isTextBox:true, margin:0 });
  s.addText('The same session. One extra record, naming what the producer was watching:\n\n'
    + '  attached          /v1/chat\n  unattached_here   /v1/responses\n  basis             route table at startup',
    { x:7.15, y:3.0, w:5.1, h:1.8, fontSize:13, color:'1E5C47', fontFace:'Courier New',
      isTextBox:true, margin:0, lineSpacingMultiple:1.15 });
  s.addText('That is the entire difference between the two files.', { x:7.15, y:5.2, w:5.1,
    h:0.5, fontSize:14, bold:true, color:'1E5C47', fontFace:BODY, isTextBox:true, margin:0 });
  foot(s, 'Proved, not exhibited: loss_accounting_is_blind_to_an_unhooked_source — every function of the delivered set and the loss declarations returns the same answer for both.');
  s.addNotes('This is the slide that wins the room. Both files pass everything. The proof says no '
    + 'cleverer verifier exists, because the inputs are byte-identical.');
}

/* ------------------------------------------------------------- 5 the ladder */
{ const s = dark();
  title(s, 'Six levels, strictly ordered, each one necessary', 'L0 to L5. Each rung refuses an attack the rung below admits — proved, not asserted.', true);
  const rows = [
    ['L1','Tamper-evident','alteration, reordering, truncation','editing the record', MINT],
    ['L2','Loss-accounted','the completeness identity closes in-chain','the silent drop', MINT],
    ['L3','Coverage-declared','the observation surface is enumerated','the unhooked source', AMB],
    ['L4','Policy-bound','verdicts bound to the rules that made them','the after-the-fact rule swap', AMB],
    ['L5','Independently witnessed','the record was not written by its subject','the forged self-report', RED],
  ];
  let y = 2.15;
  rows.forEach(r => {
    s.addShape(p.ShapeType.roundRect, { x:0.75, y, w:W-1.5, h:0.82, fill:{ color:PANEL },
      rectRadius:0.08, line:{ color:LINE, width:1 } });
    s.addShape(p.ShapeType.ellipse, { x:0.95, y:y+0.16, w:0.5, h:0.5, fill:{ color:r[4] } });
    s.addText(r[0], { x:0.95, y:y+0.16, w:0.5, h:0.5, fontSize:14, bold:true, align:'center',
      valign:'middle', color:'101826', fontFace:HEAD, isTextBox:true, margin:0 });
    s.addText(r[1], { x:1.65, y:y+0.1, w:2.9, h:0.62, fontSize:15, bold:true, color:TXT,
      fontFace:HEAD, isTextBox:true, margin:0, valign:'middle' });
    s.addText(r[2], { x:4.6, y:y+0.1, w:4.3, h:0.62, fontSize:12.5, color:MUT, fontFace:BODY,
      isTextBox:true, margin:0, valign:'middle' });
    s.addText('refuses  ' + r[3], { x:8.95, y:y+0.1, w:3.4, h:0.62, fontSize:12.5, italic:true,
      color:r[4], fontFace:BODY, isTextBox:true, margin:0, valign:'middle' });
    y += 0.93;
  });
  foot(s, 'VLC-1 §4–§7A · 26 machine-checked results, 0 admitted, 0 axioms. Every report gives TWO numbers — what the checker recomputed, and what the producer asserted (§8.4).');
  s.addNotes('The claim to make here is the strictness: for every adjacent pair there is a log that '
    + 'satisfies the lower and not the higher, and an attack the higher refuses.');
}

/* --------------------------------------------------------- 6 where everyone is */
{ const s = light();
  title(s, 'We scored four public log formats', 'From their own published specifications. None of them is badly engineered — integrity was specified; completeness never was.', false);
  s.addChart(p.ChartType.bar, [{
      name:'VLC-1 level demonstrated',
      labels:['OpenTelemetry\n(OTLP logs)','Kubernetes\naudit','Linux\nauditd','AWS CloudTrail\ndigests','Agent tool-call\ntranscripts','This project\n(live capture)'],
      values:[0, 0, 0, 0, 0, 5]
    }],
    { x:0.7, y:2.1, w:7.4, h:4.3, barDir:'col', chartColors:[ '2F4A73' ],
      showTitle:false, showLegend:false, showValue:true, dataLabelPosition:'outEnd',
      dataLabelColor:'101826', dataLabelFontSize:13, dataLabelFontBold:true,
      valAxisMaxVal:5, valAxisMajorUnit:1,
      catAxisLabelColor:'44556F', valAxisLabelColor:'8494AC', catAxisLabelFontSize:10,
      valGridLine:{ color:'E6EBF3', size:1 }, catGridLine:{ style:'none' } });
  s.addText('What stops them', { x:8.5, y:2.1, w:4.1, h:0.4, fontSize:17, bold:true,
    color:'101826', fontFace:HEAD, isTextBox:true, margin:0 });
  s.addText([
    { text:'OpenTelemetry — drops are counted, on the metrics path, unbound to the data', options:{ bullet:true, breakLine:true } },
    { text:'Kubernetes — auditID is a random UID, not an ordinal; queue drops raise a metric', options:{ bullet:true, breakLine:true } },
    { text:'auditd — the kernel counts lost records and writes the count to dmesg', options:{ bullet:true, breakLine:true } },
    { text:'CloudTrail — a real chain over files, but no end marker and no dropped-event count', options:{ bullet:true, breakLine:true } },
    { text:'Agent transcripts — written by the process being audited', options:{ bullet:true } },
  ], { x:8.5, y:2.6, w:4.1, h:3.6, fontSize:12, color:'44556F', fontFace:BODY, isTextBox:true,
       margin:0, paraSpaceAfter:9, lineSpacingMultiple:1.1 });
  s.addText('Three of the four are one afternoon-sized change from L2.', { x:8.5, y:6.25, w:4.1,
    h:0.4, fontSize:12.5, bold:true, italic:true, color:'A8341F', fontFace:BODY, isTextBox:true, margin:0 });
  foot(s, 'Adapters, samples and sources ship in the repository. Disagree by editing a JSON file and re-running — a shorter argument than an email.');
  s.addNotes('Be generous about the other products here. The point is that nobody was asked, not '
    + 'that anybody failed.');
}

/* ------------------------------------------------------ 7 the July 2026 finding */
{ const s = dark();
  title(s, 'July 2026: agents rewrote their own audit trail', 'METR and Redwood, investigating an incident involving roughly 1,200 agents.', true);
  stat(s, 0.85, 2.3, 3.3, '≥7%', 'of transcripts showed CONFIRMED spoofed tool calls — the agent issued one command and ran another', RED, true);
  stat(s, 4.55, 2.3, 3.3, '~10%', 'of relevant activity was never captured at all, partly through container resets that destroyed evidence', RED, true);
  stat(s, 8.25, 2.3, 4.2, '1,200', 'agents; the investigators note the cases they caught were crude, and competent spoofing "may have been harder to detect by design"', AMB, true);
  s.addShape(p.ShapeType.roundRect, { x:0.85, y:5.0, w:W-1.7, h:1.4, fill:{ color:PANEL },
    rectRadius:0.1, line:{ color:LINE, width:1 } });
  s.addText('Every audit trail in the AI stack today — tool-call logs, SDK traces, gateway records — '
    + 'is written by, or beside, the process being audited. When the auditee controls the recorder, '
    + 'the record is a claim. Sign it and you have a tamper-evident claim.',
    { x:1.15, y:5.25, w:W-2.3, h:0.95, fontSize:15, color:TXT, fontFace:BODY, isTextBox:true,
      margin:0, lineSpacingMultiple:1.2 });
  foot(s, 'METR / Redwood, Hugging Face incident investigation report, August 2026; OpenAI, "The Hugging Face incident and the road ahead".');
  s.addNotes('This is the slide that converts a compliance conversation into a security one. It is '
    + 'also the newest, so most buyers will not have seen it.');
}

/* ---------------------------------------------------- 8 why self-report can't fix */
{ const s = light();
  title(s, 'No amount of care with that transcript helps', 'Because the record and the behaviour it describes have the same author.', false);
  s.addShape(p.ShapeType.roundRect, { x:0.75, y:2.2, w:11.8, h:1.55, fill:{ color:'F4F7FC' },
    rectRadius:0.12, line:{ color:'DCE4F0', width:1 } });
  s.addText('no_check_on_the_self_report_can_see_substitution', { x:1.05, y:2.42, w:11.2, h:0.42,
    fontSize:17, bold:true, fontFace:'Courier New', color:'101826', isTextBox:true, margin:0 });
  s.addText('For any two behaviours and any self-report, EVERY function of the self-report returns '
    + 'the same answer. The quantifier is the whole content — there is no cleverer check.',
    { x:1.05, y:2.92, w:11.2, h:0.7, fontSize:14, color:'44556F', fontFace:BODY, isTextBox:true,
      margin:0, lineSpacingMultiple:1.15 });
  card(s, 0.75, 4.05, 5.7, 2.45, MINT, '1', 'Reconcile, in both directions',
    'claimed-and-not-witnessed  +  witnessed-and-not-claimed.\nReporting one direction detects half a substitution, which is not a detection.', false);
  card(s, 6.85, 4.05, 5.7, 2.45, AMB, '2', 'The witness must itself be complete',
    'A witness with an undeclared coverage gap agrees with a lie honestly. VLC-L5-4 requires the witnessing log to hold L3 in its own right.', false);
  foot(s, 'VLC-1 §7A · witness/reconcile.py · demo 08 asserts silence on an honest run and the substitution signature on a spoofed one.');
}

/* --------------------------------------------------------------- 9 what we built */
{ const s = dark();
  title(s, 'A record the workload cannot write', 'Kernel-level evidence for AI systems — three properties, in the order buyers ask about them.', true);
  card(s, 0.7, 2.25, 3.9, 3.9, MINT, 'C', 'Complete, checkably',
    'Records the sensor could not deliver are declared in-chain with a count.\n\n'
  + 'Syscalls the sensor is NOT attached to are declared too — the blind spot no gap '
  + 'record could ever reveal, because an unhooked syscall produces no decision to lose.', true);
  card(s, 4.75, 2.25, 3.9, 3.9, AMB, 'I', 'Independent',
    'The audited process does not write it, cannot edit it, and cannot quietly detach it.\n\n'
  + 'This is the property that matters after July 2026 — and the one no SDK, gateway, '
  + 'proxy or framework hook can acquire by trying harder.', true);
  card(s, 8.8, 2.25, 3.8, 3.9, 'CADCFC', 'P', 'Proved',
    'The decision logic is machine-checked in Coq, and the proved function is shown to '
  + 'agree with the C that ships over its ENTIRE input domain.\n\n'
  + 'Not sampled. Not fuzzed. Enumerated, with pinned digests and mutation controls.', true);
  s.addNotes('Do not lead with eBPF. eBPF is table stakes in 2026 and the incumbents have already '
    + 'bought theirs. Lead with the evidence property.');
}

/* --------------------------------------------- 9b three products, and what to ask for */
{ const s = light();
  title(s, 'Three products, one decision function', 'What is public, what you can ask for, and what is not distributed — named, so nobody has to guess.', false);
  const prods = [
    ['OCTA Sentinel', 'governs what an agent DOES\nthe Linux syscall boundary',
     'PUBLIC   the VLC-1 specification · the conformance checker and adapters · the completeness lattice proof · the witness reconciler · real captured journals',
     'ASK FOR   the proof estate · verify.sh, the one-command re-verification you run on your own hardware · the live demonstration suite · the conformity pack and auditor runbook',
     'PRIVATE   the sensor, policy engine, classifier, pinning and object tiers'],
    ['OCTA Gateway', 'governs what an agent ASKS FOR\ntool authorisation and approval',
     'PUBLIC   the requirement that a gateway declare which endpoints it terminates (VLC-L5-2) · the reconciler format, so its own record can be checked against an independent one',
     'ASK FOR   the decision-function conformance pack · the composition proof · the written security review of the layer sitting in front of the policy engine',
     'PRIVATE   gateway source'],
    ['MooreOS', 'the same govern() on BARE METAL\nW^X, post-quantum attestation',
     'PUBLIC   why an attested coverage declaration is different evidence from one a userspace daemon wrote',
     'ASK FOR   the integer inference core — no floating point, which is what makes a result attestable — and its proof binding · the bare-metal versus hosted equivalence review',
     'PRIVATE   kernel source'],
  ];
  let y = 2.15;
  prods.forEach(pr => {
    s.addShape(p.ShapeType.roundRect, { x:0.7, y, w:W-1.4, h:1.45, fill:{ color:'F4F7FC' },
      rectRadius:0.1, line:{ color:'DCE4F0', width:1 } });
    s.addText(pr[0], { x:1.0, y:y+0.13, w:3.0, h:0.38, fontSize:16, bold:true, color:'101826',
      fontFace:HEAD, isTextBox:true, margin:0 });
    s.addText(pr[1], { x:1.0, y:y+0.54, w:3.0, h:0.78, fontSize:10.5, italic:true, color:'6B7C96',
      fontFace:BODY, isTextBox:true, margin:0, valign:'top', lineSpacingMultiple:1.08 });
    s.addText([
      { text: pr[2], options:{ breakLine:true, color:'1E5C47' } },
      { text: pr[3], options:{ breakLine:true, color:'8A5A14' } },
      { text: pr[4], options:{ color:'7A8699' } },
    ], { x:4.2, y:y+0.14, w:8.1, h:1.2, fontSize:10.5, fontFace:BODY, isTextBox:true,
         margin:0, valign:'top', lineSpacingMultiple:1.14, paraSpaceAfter:3 });
    y += 1.55;
  });
  foot(s, 'ACCESS.md in the repository has the same list with the access level each item sits behind. Level 0 needs no request at all.');
  s.addNotes('This is the slide that tells a stranger what they can actually get hold of. Names only, '
    + 'on purpose: the numbers behind each item come with the request, not before it.');
}

/* ----------------------------------------------------------------- 10 the numbers */
{ const s = light();
  title(s, 'All of that is re-checkable in one command', './verify.sh — from source, nothing cached, on your hardware.', false);
  const nums = [
    ['20','verification steps, each exiting non-zero when its own claim does not hold', '2F4A73'],
    ['10','Coq developments behind it — 0 admitted, 0 axioms, every result closed under the global context', '2F4A73'],
    ['8','live demonstrations, run on the customer\'s machines in week one', '2F4A73'],
    ['4','independent re-builds from source in a cold container, reproducing every pinned digest exactly', 'A8341F'],
  ];
  let x = 0.75;
  nums.forEach(n => { stat(s, x, 2.4, 2.62, n[0], n[1], n[2], false); x += 3.07; });
  s.addShape(p.ShapeType.roundRect, { x:0.75, y:4.9, w:W-1.5, h:1.5, fill:{ color:'F4F7FC' },
    rectRadius:0.1, line:{ color:'DCE4F0', width:1 } });
  s.addText('The fourth number is the answer to the question every 2026 vendor checklist asks — '
    + '"what happens if you disappear?" The offer is source escrow plus a one-command rebuild that '
    + 'reproduces a digest you already hold. Very few vendors of any size can make that offer.',
    { x:1.05, y:5.15, w:W-2.1, h:1.0, fontSize:15, color:'44556F', fontFace:BODY, isTextBox:true,
      margin:0, lineSpacingMultiple:1.2 });
  foot(s, 'Counts as at 2026-09-12, from the run log of ./verify.sh. Every one of them is a number the script prints, not a number written here.');
}

/* ------------------------------------------------------- 11 it scored us first */
{ const s = dark();
  title(s, 'The checker cost us two levels on run one', 'A conformance suite that flatters its author is a sales tool with a test harness bolted on.', true);
  card(s, 0.75, 2.25, 5.7, 3.95, RED, '!', 'What it found, on run one',
    'Our own captured journal came out at L2, not L4.\n\n'
  + 'It failed VLC-L3-1(d): the coverage record listed the instrumented syscalls and '
  + 'never said HOW it knew the list was exhaustive. A list is not a declaration — '
  + 'you can always write a longer list.', true);
  card(s, 6.85, 2.25, 5.7, 3.95, MINT, '✓', 'What we did about it',
    'Fixed the sensor the same day, and KEPT the pre-fix capture.\n\n'
  + 'The self-test now asserts that the old capture still comes out at L2. A future '
  + 'change that makes it pass is a loosened checker, not an improved product — and '
  + 'the test will say so.', true);
  foot(s, 'examples/reference-impl/pre-basis-L2.jsonl · selftest.sh §5 "NOT RIGGED"');
  s.addNotes('Use this slide when someone asks whether the spec is self-serving. It is the most '
    + 'persuasive thing in the deck and it costs nothing to say.');
}

/* ------------------------------------------------------------- 12 the window */
{ const s = light();
  title(s, 'The standards defining this are being written now', 'And the window in which completeness can enter them is measured in weeks, not years.', false);
  const items = [
    ['prEN 18229-1','AI system logging (CEN-CENELEC JTC 21)','Enquiry closed — comment disposition IN PROGRESS', AMB],
    ['prEN 18229-3','Transparency and human oversight','AT PUBLIC ENQUIRY', RED],
    ['ISO/IEC 24970','AI system logging','FDIS — last stage before publication', '8494AC'],
    ['EU AI Act','Articles 9–15','Apply from 2 December 2027', '2F4A73'],
  ];
  let y = 2.2;
  items.forEach(it => {
    s.addShape(p.ShapeType.roundRect, { x:0.75, y, w:W-1.5, h:0.95, fill:{ color:'F4F7FC' },
      rectRadius:0.08, line:{ color:'DCE4F0', width:1 } });
    s.addShape(p.ShapeType.ellipse, { x:0.98, y:y+0.3, w:0.34, h:0.34, fill:{ color:it[3] } });
    s.addText(it[0], { x:1.5, y:y+0.12, w:2.9, h:0.7, fontSize:16, bold:true, color:'101826',
      fontFace:HEAD, isTextBox:true, margin:0, valign:'middle' });
    s.addText(it[1], { x:4.45, y:y+0.12, w:4.2, h:0.7, fontSize:13, color:'44556F',
      fontFace:BODY, isTextBox:true, margin:0, valign:'middle' });
    s.addText(it[2], { x:8.7, y:y+0.12, w:3.7, h:0.7, fontSize:12.5, bold:true, color:it[3],
      fontFace:BODY, isTextBox:true, margin:0, valign:'middle' });
    y += 1.0;
  });
  s.addText('None of them currently requires anything in VLC-1. The specification is published '
    + 'CC0 so a committee can lift clauses verbatim — a specification a standards body cannot copy '
    + 'from is a brochure.', { x:0.75, y:6.45, w:W-1.5, h:0.6, fontSize:13, italic:true,
      color:'44556F', fontFace:BODY, isTextBox:true, margin:0 });
  s.addNotes('Status as at 12 September 2026. Re-check dates before presenting — this slide goes '
    + 'stale faster than any other.');
}

/* --------------------------------------------------------------- 13 access */
{ const s = dark();
  title(s, 'Four levels of access', 'The first one needs no request, no email and no form — and we would rather you used it.', true);
  const lv = [
    ['0', 'Use it', 'FREE · no contact at all', 'CADCFC',
     'Clone the repository and run ./selftest.sh. Score your own logs with the checker. '
   + 'If you come out at L3 or above, you do not need us, and we would rather you knew that today.'],
    ['1', 'Score my format', 'FREE · no NDA', MINT,
     'Open an issue with your log’s FIELD NAMES — never the values — and we write the adapter and '
   + 'send it back. No charge and no obligation: a third party’s log being scorable by this checker '
   + 'is worth more to us than a meeting.'],
    ['2', 'Evaluation', 'FREE · mutual NDA', AMB,
     'The proof estate, the one-command re-verification so you re-check every claim from source on '
   + 'your own hardware, the conformity pack and the demonstrations. This level exists because we do '
   + 'not present numbers you cannot reproduce.'],
    ['3', 'Pilot, or escrow', 'PAID · scoped in writing', RED,
     'The sensor on your hardware, on your workload, from week one — and an evidence package an '
   + 'assessor can verify without our software. Ask and we will quote: a number without a scope is '
   + 'not a price.'],
  ];
  let y = 2.1;
  lv.forEach(l => {
    s.addShape(p.ShapeType.roundRect, { x:0.7, y, w:W-1.4, h:1.06, fill:{ color:PANEL },
      rectRadius:0.09, line:{ color:LINE, width:1 } });
    s.addShape(p.ShapeType.ellipse, { x:0.95, y:y+0.27, w:0.52, h:0.52, fill:{ color:l[3] } });
    s.addText(l[0], { x:0.95, y:y+0.27, w:0.52, h:0.52, fontSize:15, bold:true, align:'center',
      valign:'middle', color:'101826', fontFace:HEAD, isTextBox:true, margin:0 });
    s.addText(l[1], { x:1.65, y:y+0.13, w:2.5, h:0.42, fontSize:15, bold:true, color:TXT,
      fontFace:HEAD, isTextBox:true, margin:0 });
    s.addText(l[2], { x:1.65, y:y+0.55, w:2.5, h:0.38, fontSize:11, color:l[3], fontFace:BODY,
      isTextBox:true, margin:0 });
    s.addText(l[4], { x:4.3, y:y+0.13, w:7.95, h:0.86, fontSize:11.5, color:MUT, fontFace:BODY,
      isTextBox:true, margin:0, valign:'top', lineSpacingMultiple:1.13 });
    y += 1.16;
  });
  foot(s, 'ACCESS.md has the full matrix. For calibration from published third-party sources and not from us: runtime sensors in this market list around $250–400 per host per year.');
  s.addNotes('Never quote a pilot price from the stage — the point of level 3 is that scope comes first. '
    + 'The market anchor in the footer is somebody else’s published number, which is why it is safe to show.');
}

/* ------------------------------------------------------ 14 what it does not do */
{ const s = light();
  title(s, 'What this does not do', 'A vendor whose limits you have to discover is one you will discover them from at the worst moment.', false);
  const lim = [
    ['It is not a guardrail.','It records, and can deny at the syscall boundary. It does not understand intent and will not stop a well-formed action that should not have been taken.'],
    ['It does not see inside TLS.','A destructive query over an authorised connection appears as a connection.'],
    ['It does not stop rendered-URL exfiltration or a tool description that lies.','Those failures produce syntactically normal syscalls. We will say so rather than sell coverage we do not have.'],
    ['It needs a governed tree the workload cannot write.','Where that is impossible, the record says unverified and why — rather than a bit that quietly means something else.'],
    ['No SOC 2, no ISO 27001, not yet.','The continuity answer on slide 10 is what we offer instead, and it is a tested property rather than a promise.'],
  ];
  let y = 2.15;
  lim.forEach(l => {
    s.addShape(p.ShapeType.ellipse, { x:0.8, y:y+0.09, w:0.26, h:0.26, fill:{ color:'C9D4E6' } });
    s.addText(l[0], { x:1.25, y, w:4.3, h:0.85, fontSize:14, bold:true, color:'101826',
      fontFace:HEAD, isTextBox:true, margin:0, valign:'top' });
    s.addText(l[1], { x:5.65, y, w:6.9, h:0.85, fontSize:12.5, color:'44556F', fontFace:BODY,
      isTextBox:true, margin:0, valign:'top', lineSpacingMultiple:1.1 });
    y += 0.92;
  });
  foot(s, 'This slide is in the deck on purpose. It is the one buyers remember.');
}

/* ------------------------------------------------------------------ 15 close */
{ const s = dark();
  s.addShape(p.ShapeType.ellipse, { x:-1.8, y:H-3.2, w:5.2, h:5.2, fill:{ color:'16233A' } });
  s.addText('Request access \u2014 or don\u2019t, and just run it', { x:1.1, y:1.15, w:10.5, h:0.6,
    fontSize:15, bold:true, charSpacing:3, color:AMB, fontFace:BODY, isTextBox:true, margin:0 });
  s.addText([
    { text:'“Here are our log field names — what level are we?”', options:{ breakLine:true } },
    { text:'“Clause VLC-Lx-y looks like it was written around your product.”', options:{ breakLine:true } },
    { text:'“We have an assessment in <month> and we need to answer the completeness question.”', options:{} },
  ], { x:1.1, y:1.95, w:10.8, h:2.4, fontSize:24, color:TXT, fontFace:HEAD, isTextBox:true,
       margin:0, lineSpacingMultiple:1.35 });
  s.addShape(p.ShapeType.roundRect, { x:1.1, y:4.6, w:10.8, h:1.45, fill:{ color:PANEL },
    rectRadius:0.1, line:{ color:LINE, width:1 } });
  s.addText('Matthew Moore', { x:1.45, y:4.8, w:5.0, h:0.45, fontSize:22, bold:true, color:TXT,
    fontFace:HEAD, isTextBox:true, margin:0 });
  s.addText('moorematthew131@gmail.com', { x:1.45, y:5.28, w:5.6, h:0.45, fontSize:17, color:AMB,
    fontFace:BODY, isTextBox:true, margin:0 });
  s.addText('Open an issue with the Access request template, or\nemail for anything confidential. '
    + 'ACCESS.md names what\nsits behind each level.', { x:7.0, y:4.8, w:4.7, h:1.1, fontSize:12,
      color:MUT, fontFace:BODY, isTextBox:true, margin:0, lineSpacingMultiple:1.2 });
  s.addText('VLC-1 · Verifiable Completeness for AI System Logs', { x:1.1, y:H-0.85, w:8, h:0.4,
    fontSize:11, charSpacing:2, color:'6F87AA', fontFace:BODY, isTextBox:true, margin:0 });
}

p.writeFile({ fileName: 'VLC-1.pptx' }).then(() => console.log('written'));
