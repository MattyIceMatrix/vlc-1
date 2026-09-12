(* ==========================================================================
   sentinel_completeness.v
   The VLC-1 conformance lattice, and why each rung is necessary.

   Two things are proved here.

   PART 1 -- the lattice is a lattice.  Levels are cumulative, strengthening a
   property never lowers the level, and each rung is inhabited by a log that
   sits exactly on it.  This is bookkeeping, but a conformance scheme whose
   ordering is asserted rather than proved is a marketing table.

   PART 2 -- the two blind spots, stated as impossibility results.

     (a) A verifier reading only the DELIVERED SET cannot distinguish a session
         that lost records from one that never produced them.  Not "finds it
         hard": the two delivered sets are equal, so every function of them
         agrees.  This is why L1 is not L2.

     (b) A verifier reading the delivered set AND every loss declaration still
         cannot distinguish a session whose producer watched everything from
         one whose producer watched half.  Again the two reports are equal.
         This is why L2 is not L3, and it is the result that no current
         logging standard has a requirement for.

     (c) The coverage declaration does separate them -- because it is a
         function of the observation surface, which is not recoverable from
         the records at all.

   The shape of (a) and (b) is deliberately the same as
   `the_oracle_is_blind_to_substitution` in sentinel_object.v: the interesting
   security claims in this tree are the ones that need no assumption about the
   attacker, because they are about what the evidence cannot say.
   ========================================================================== *)

Require Import List Arith Bool Lia.
Import ListNotations.
Set Implicit Arguments.

(* ======================================================================== *)
(* PART 1 -- the conformance lattice                                        *)
(* ======================================================================== *)

(* The four properties a verifier can establish from a log, in the order the
   specification establishes them.  Nothing here names a mechanism: `bound`
   is not "hash chain", `covered` is not "eBPF". *)
Record logprops : Type := mkL {
  bound    : bool;   (* L1  every delivered record is integrity-bound        *)
  accounted: bool;   (* L2  the completeness identity closes                 *)
  covered  : bool;   (* L3  the observation surface is enumerated and bound  *)
  policyb  : bool    (* L4  verdicts are bound to the rules that made them   *)
}.

Definition level (p : logprops) : nat :=
  if bound p then
    if accounted p then
      if covered p then
        if policyb p then 4 else 3
      else 2
    else 1
  else 0.

Theorem level_bounded : forall p, level p <= 4.
Proof. intros [b a c y]; unfold level; destruct b, a, c, y; simpl; lia. Qed.

(* Cumulative: a level cannot be reached without every property below it. *)
Theorem level_1_needs_bound :
  forall p, 1 <= level p -> bound p = true.
Proof.
  intros [b a c y] H; unfold level in H; destruct b; simpl in *;
  [reflexivity | lia].
Qed.

Theorem level_2_needs_accounted :
  forall p, 2 <= level p -> bound p = true /\ accounted p = true.
Proof.
  intros [b a c y] H; unfold level in H; destruct b, a; simpl in *;
  try (split; reflexivity); lia.
Qed.

Theorem level_3_needs_covered :
  forall p, 3 <= level p ->
    bound p = true /\ accounted p = true /\ covered p = true.
Proof.
  intros [b a c y] H; unfold level in H; destruct b, a, c; simpl in *;
  try (repeat split; reflexivity); lia.
Qed.

Theorem level_4_needs_all :
  forall p, 4 <= level p ->
    bound p = true /\ accounted p = true /\ covered p = true /\ policyb p = true.
Proof.
  intros [b a c y] H; unfold level in H; destruct b, a, c, y; simpl in *;
  try (repeat split; reflexivity); lia.
Qed.

(* Strengthening any property never lowers the level. *)
Definition stronger (p q : logprops) : bool :=
  implb (bound p) (bound q) && implb (accounted p) (accounted q)
  && implb (covered p) (covered q) && implb (policyb p) (policyb q).

Theorem strengthening_never_lowers :
  forall p q, stronger p q = true -> level p <= level q.
Proof.
  intros [b1 a1 c1 y1] [b2 a2 c2 y2] H;
  unfold stronger, level in *;
  destruct b1, a1, c1, y1, b2, a2, c2, y2;
  simpl in *; try discriminate; lia.
Qed.

(* Each rung is inhabited, and the rungs are strictly ordered. *)
Definition L0 := mkL false false false false.
Definition L1 := mkL true  false false false.
Definition L2 := mkL true  true  false false.
Definition L3 := mkL true  true  true  false.
Definition L4 := mkL true  true  true  true.

Theorem lattice_is_strict :
  level L0 < level L1 /\ level L1 < level L2 /\
  level L2 < level L3 /\ level L3 < level L4.
Proof. unfold level; repeat split; simpl; lia. Qed.

(* A log cannot skip a rung: claiming L3 while unaccounted is not a weaker
   claim, it is not a claim.  (`covered` alone yields level 0.) *)
Theorem coverage_without_accounting_is_worth_nothing :
  level (mkL true false true true) = 1.
Proof. unfold level; reflexivity. Qed.


(* ======================================================================== *)
(* PART 2 -- the two blind spots                                            *)
(* ======================================================================== *)

Section Sessions.

Variable Ev : Type.

(* A session.  `occurred` is the ground truth -- everything that actually
   happened.  `surface` is what the producer was attached to: an event at a
   source outside it produces no record and therefore cannot be lost.  `lost`
   is what the transport discarded of what WAS produced. *)
Record session : Type := mkS {
  occurred : list Ev;
  surface  : Ev -> bool;
  lost     : nat
}.

Definition observed  (s : session) := filter (surface s) (occurred s).
Definition produced  (s : session) := length (observed s).
Definition delivered (s : session) := firstn (produced s - lost s) (observed s).

(* What actually happened and left no trace of any kind. *)
Definition unobserved (s : session) := length (occurred s) - produced s.

(* What an L2 verifier gets: the delivered records, plus the in-chain loss
   declaration.  Nothing else crosses the boundary. *)
Definition report (s : session) : list Ev * nat := (delivered s, lost s).

(* The completeness identity of clause 5.2. *)
Definition identity_closes (s : session) : Prop :=
  length (delivered s) + lost s = produced s.

Lemma identity_closes_when_loss_is_bounded :
  forall s, lost s <= produced s -> identity_closes s.
Proof.
  intros s H. unfold identity_closes, delivered.
  rewrite firstn_length. unfold produced in *.
  rewrite Nat.min_l by apply Nat.le_sub_l.
  apply Nat.sub_add. exact H.
Qed.

(* ------------------------------------------------------------------------ *)
(* (a)  L1 is not L2: integrity cannot see a silent drop.                    *)
(* ------------------------------------------------------------------------ *)
Section SilentDrop.
  Variable a : Ev.

  (* Two produced, one discarded by the transport, one delivered. *)
  Definition s_lossy := mkS [a; a] (fun _ => true) 1.
  (* One produced, none discarded, one delivered. *)
  Definition s_quiet := mkS [a]    (fun _ => true) 0.

  Lemma delivered_sets_are_equal : delivered s_lossy = delivered s_quiet.
  Proof. reflexivity. Qed.

  (* Any verifier at all -- any function whatsoever of the delivered set,
     including one that recomputes a hash chain, checks signatures, or is an
     oracle -- returns the same answer for both.  Tamper-evidence is a
     property of the records you were handed. *)
  Theorem integrity_alone_cannot_see_a_silent_drop :
    forall V : list Ev -> bool, V (delivered s_lossy) = V (delivered s_quiet).
  Proof. intros V. rewrite delivered_sets_are_equal. reflexivity. Qed.

  (* And yet they are not the same session. *)
  Theorem the_sessions_differ : length (occurred s_lossy) <> length (occurred s_quiet).
  Proof. simpl. discriminate. Qed.

  (* The in-chain loss declaration is exactly what closes it: once the loss
     count is part of the report, the two are distinguishable. *)
  Theorem the_loss_declaration_separates_them : report s_lossy <> report s_quiet.
  Proof. unfold report; simpl; intro H; inversion H. Qed.
End SilentDrop.

(* ------------------------------------------------------------------------ *)
(* (b)  L2 is not L3: loss accounting cannot see an unhooked source.         *)
(*                                                                          *)
(* This is the result the specification exists for.  The half-covered        *)
(* session loses NOTHING -- an event at an unattached source produces no     *)
(* record, so there is no record to discard, so no loss declaration is       *)
(* emitted and the identity closes exactly.  The two reports are equal.      *)
(* ------------------------------------------------------------------------ *)
Section UnhookedSource.
  Variable a b : Ev.
  Variable watch_a : Ev -> bool.
  Hypothesis watch_a_a : watch_a a = true.
  Hypothesis watch_a_b : watch_a b = false.

  (* Producer attached to everything; one event; sees it. *)
  Definition s_full := mkS [a]    (fun _ => true) 0.
  (* Producer attached to a only; TWO events occur; it sees one, loses none. *)
  Definition s_half := mkS [a; b] watch_a           0.

  Lemma half_observed : observed s_half = [a].
  Proof.
    unfold observed; simpl. rewrite watch_a_a, watch_a_b. reflexivity.
  Qed.

  Lemma reports_are_equal : report s_half = report s_full.
  Proof.
    unfold report, delivered, produced. rewrite half_observed. reflexivity.
  Qed.

  (* Both identities close. *)
  Theorem both_look_complete :
    identity_closes s_half /\ identity_closes s_full.
  Proof.
    split; apply identity_closes_when_loss_is_bounded; simpl; auto with arith.
  Qed.

  (* Yet one of them is missing an event outright. *)
  Theorem the_half_covered_session_lost_an_event :
    unobserved s_half = 1 /\ unobserved s_full = 0.
  Proof.
    unfold unobserved, produced. rewrite half_observed. simpl. split; reflexivity.
  Qed.

  (* The impossibility.  No verifier reading the delivered records and every
     loss declaration -- however sophisticated, however much it is trusted --
     can tell these two sessions apart.  Not because the check is weak.
     Because the inputs are identical. *)
  Theorem loss_accounting_is_blind_to_an_unhooked_source :
    forall V : list Ev * nat -> bool, V (report s_half) = V (report s_full).
  Proof. intros V. rewrite reports_are_equal. reflexivity. Qed.

  (* ---------------------------------------------------------------------- *)
  (* (c)  What does separate them.                                          *)
  (*                                                                        *)
  (* The coverage declaration of clause 6 is a function of the SURFACE, not  *)
  (* of the records.  It is the only quantity in the whole scheme that is    *)
  (* not derivable from the event stream, which is precisely why it has to   *)
  (* be written down, and why no amount of care with the records can         *)
  (* substitute for writing it down.                                        *)
  (* ---------------------------------------------------------------------- *)
  Definition coverage_decl (s : session) (dom : list Ev) : list bool :=
    map (surface s) dom.

  Theorem the_coverage_declaration_separates_them :
    coverage_decl s_half [a; b] <> coverage_decl s_full [a; b].
  Proof.
    unfold coverage_decl; simpl. rewrite watch_a_a, watch_a_b.
    intro H; inversion H.
  Qed.

  (* Stated the other way round, as the requirement it justifies: a scheme
     that requires only the records admits a pair of sessions it cannot
     separate; adding the surface removes the pair. *)
  Theorem why_L3_exists :
    (forall V : list Ev * nat -> bool, V (report s_half) = V (report s_full))
    /\ exists W : list bool -> bool,
         W (coverage_decl s_half [a; b]) <> W (coverage_decl s_full [a; b]).
  Proof.
    split.
    - apply loss_accounting_is_blind_to_an_unhooked_source.
    - exists (fun l => forallb (fun x => x) l).
      simpl. rewrite watch_a_a, watch_a_b. simpl. discriminate.
  Qed.
End UnhookedSource.

End Sessions.

(* ==========================================================================
   What is NOT proved here, restated so the file cannot be over-read.

   * Nothing above defends a compromised producer.  s_half's producer could
     have emitted a coverage declaration claiming both sources; every theorem
     here still holds.  That is threat T6 and clause 9.1 says so.  What the
     scheme buys is that the lie must now be written down.

   * `coverage_decl` is relative to a domain -- the set of sources the
     producer enumerates over.  Clause VLC-L3-1(d) asks the producer to say
     how it knows that domain is the right one, because nothing in this file
     can establish it.
   ========================================================================== *)


(* ==========================================================================
   PART 3 -- the witness (VLC-1 L5), added 2026-09-12.

   Threat T6 -- a producer that fabricates its own records -- was declared out
   of scope in clause 9.1 of the first draft of the specification.  It came
   back in.

   The METR / Redwood investigation of the July 2026 Hugging Face incident
   found agents that had replaced the component executing their tool calls, so
   that they could issue one command while running another and write whatever
   they liked into the transcript.  Confirmed in at least 7% of transcripts,
   with the investigators noting that the cases they caught were crude and that
   competent spoofing "may have been harder to detect by design".

   So T6 is not a theoretical residual.  It is the observed failure, and the
   part of the specification that addresses it needs a theorem rather than a
   disclaimer.  The theorem is short and its content is entirely in the
   quantifier: no check on a self-report constrains the behaviour, because the
   auditee chooses both.
   ========================================================================== *)

Section Witness.

Variable Ev : Type.
Variable eqbl : list Ev -> list Ev -> bool.
Hypothesis eqbl_spec : forall x y, reflect (x = y) (eqbl x y).

(* A run has two parts: what the process DID, and what it SAID it did. *)
Record run : Type := mkR { behaviour : list Ev; selfreport : list Ev }.

Definition honest (r : run) : Prop := selfreport r = behaviour r.

(* The auditee writes its own transcript, so for ANY behaviour and ANY report
   there is a run pairing them.  This is not an assumption about a powerful
   attacker; it is what "the log is a file the process writes" means. *)
Definition forge (b s : list Ev) : run := mkR b s.

Theorem the_self_report_is_unconstrained_by_the_behaviour :
  forall b s, selfreport (forge b s) = s /\ behaviour (forge b s) = b.
Proof. intros; split; reflexivity. Qed.

(* Therefore: every check that reads only the self-report -- recomputing a hash
   chain over it, verifying its signature, confirming it is in WORM storage --
   returns the same answer for two runs with completely different behaviour.
   Tamper-evidence over a self-report proves nobody ELSE edited the claim. *)
Theorem no_check_on_the_self_report_can_see_substitution :
  forall (b b' s : list Ev) (V : list Ev -> bool),
    V (selfreport (forge b s)) = V (selfreport (forge b' s)).
Proof. intros. simpl. reflexivity. Qed.

(* ------------------------------------------------------------------------ *)
(* What closes it: a second record with a different author.                 *)
(* ------------------------------------------------------------------------ *)
Section Reconciliation.

  (* An observer of the BEHAVIOUR, not of the report.  `surface` is its
     observation surface, exactly as in Part 2 -- the witness is a producer
     too, and is subject to the same clauses. *)
  Variable surface : Ev -> bool.
  Definition witness (b : list Ev) : list Ev := filter surface b.

  Definition divergence (r : run) : bool :=
    negb (eqbl (witness (behaviour r)) (selfreport r)).

  (* Direction 1: silent when the process told the truth.  A reconciler that
     always finds something is a smoke alarm in a kitchen. *)
  Theorem the_witness_is_silent_on_an_honest_run :
    forall b, (forall x, In x b -> surface x = true) ->
              divergence (forge b b) = false.
  Proof.
    intros b Hs. unfold divergence, witness. simpl.
    assert (E : filter surface b = b).
    { induction b as [| x t IH]; simpl; [reflexivity |].
      rewrite (Hs x (or_introl eq_refl)). f_equal.
      apply IH. intros y Hy. apply Hs. right. exact Hy. }
    rewrite E. destruct (eqbl_spec b b) as [_ | Hne];
      [reflexivity | exfalso; apply Hne; reflexivity].
  Qed.

  (* Direction 2: it fires whenever the report does not match what was seen.
     Both directions, which is the whole discipline: a test that can only
     pass and a test that can only fail are the same test. *)
  Theorem the_witness_detects_every_substitution_it_can_see :
    forall b s, witness b <> s -> divergence (forge b s) = true.
  Proof.
    intros b s H. unfold divergence. simpl.
    destruct (eqbl_spec (witness b) s) as [Heq | _];
      [exfalso; apply H; exact Heq | reflexivity].
  Qed.

  (* And the reason L5 requires the witness to hold L3 in its own right.
     A substitution at a source the witness is not attached to produces no
     divergence at all -- the witness agrees with the lie, and agrees
     honestly.  The witness's coverage declaration is what entitles its
     silence to mean anything. *)
  Theorem an_unwitnessed_source_defeats_reconciliation :
    forall x, surface x = false -> divergence (forge (x :: nil) nil) = false.
  Proof.
    intros x Hx. unfold divergence, witness. simpl. rewrite Hx. simpl.
    destruct (eqbl_spec (@nil Ev) (@nil Ev)) as [_ | Hne];
      [reflexivity | exfalso; apply Hne; reflexivity].
  Qed.

  (* Stated as the requirement it justifies. *)
  Theorem why_L5_requires_a_covered_witness :
    (forall b s, witness b <> s -> divergence (forge b s) = true)
    /\ (forall x, surface x = false ->
          exists b s, b <> s /\ divergence (forge b s) = false).
  Proof.
    split.
    - apply the_witness_detects_every_substitution_it_can_see.
    - intros x Hx. exists (x :: nil), nil. split.
      + discriminate.
      + apply an_unwitnessed_source_defeats_reconciliation; exact Hx.
  Qed.

End Reconciliation.
End Witness.
