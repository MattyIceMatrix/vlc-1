(* ==========================================================================
   sentinel_interval.v
   Producer death, and why interval attestation is the repair.

   PROVENANCE -- read this before citing the file.

   A file of this name was cited in five places in this repository -- a
   normative sentence in SPEC.md, CORRIGENDUM-2026-09-13-01.md ("8 results,
   0 admitted, 0 axioms"), the fix claim for EXT-002, and twice in
   check_l3i.py -- and was never in the tree. EXT-019 records that, and
   records that the CI proof step globs proofs/*.v and so could not notice.

   THIS FILE IS NOT THAT DEVELOPMENT. It was written on 2026-09-27 to make
   the citations true, and it proves the two results they name from scratch.
   It claims no continuity with whatever was originally meant, and it has
   eight results because that is what the work needed, not to match the
   number the corrigendum printed. If the original is ever recovered, the two
   should be compared rather than one silently replacing the other.

   WHAT IS PROVED.

   PART 1 -- producer death is invisible to L2. The completeness identity is
   computed from quantities the PRODUCER declares. A producer that dies
   mid-session declares neither the records it never wrote nor a loss it
   never noticed, so its account of a truncated session is EQUAL to its
   account of a session that was genuinely that short. Equal, not merely
   similar: every function of the account agrees, so no L2 verifier -- none,
   however clever -- separates them.

   PART 2 -- interval attestation separates them. A declared interval whose
   every tick is witnessed by an attestor the producer does not control is a
   function of something the producer cannot suppress by dying. The missing
   ticks are the evidence the producer's own silence cannot supply.

   The correspondence check_l3i.py relies on is stated at the end, so a
   differential has something written down to differ from.
   ========================================================================== *)

Require Import List Arith Bool Lia.
Import ListNotations.
Set Implicit Arguments.

Section Interval.

Variable Ev : Type.

(* ======================================================================== *)
(* PART 1 -- producer death is invisible to L2                              *)
(* ======================================================================== *)

(* What crosses the boundary to an L2 verifier. Every quantity here is one
   the PRODUCER supplies: the records it delivered, the loss it declared, and
   the count it declared having produced. A verifier has nothing else. That
   is the whole of the hypothesis. *)
Record account : Type := mkA {
  adelivered : list Ev;
  alost      : nat;
  aproduced  : nat
}.

(* The completeness identity of clause 5.2, over declared quantities. *)
Definition closes (x : account) : Prop :=
  length (adelivered x) + alost x = aproduced x.

(* A producer that survives its session declares what it delivered, what the
   transport discarded, and the total it produced. *)
Definition survived (dl : list Ev) (lost : nat) : account :=
  mkA dl lost (length dl + lost).

(* A producer that DIES after emitting a prefix declares that prefix, no
   loss -- it was not there to notice any -- and a produced count equal to
   what it managed to write. Nothing about the events it never reached
   appears anywhere, because nothing recorded them. *)
Definition died_after (dl : list Ev) : account := mkA dl 0 (length dl).

(* A session in which only those events ever happened, with nothing lost. *)
Definition genuinely_short (dl : list Ev) : account := mkA dl 0 (length dl).

(* ---- the identity closes for both, which is the trap ------------------- *)

Theorem died_account_closes : forall dl, closes (died_after dl).
Proof. intro dl. unfold closes, died_after. simpl. apply Nat.add_0_r. Qed.

Theorem short_account_closes : forall dl, closes (genuinely_short dl).
Proof. intro dl. unfold closes, genuinely_short. simpl. apply Nat.add_0_r. Qed.

(* ---- and the two accounts are the same object -------------------------- *)

Lemma death_and_brevity_agree :
  forall dl, died_after dl = genuinely_short dl.
Proof. reflexivity. Qed.

(* THE RESULT. Not "a verifier finds this hard". The two accounts are equal,
   so every function of an account whatsoever -- a hash-chain recomputation,
   a signature check, a statistical test, an oracle -- returns the same value
   for both. A checker's verdict on a renumbered truncation is EQUAL to its
   verdict on the renumbered whole. *)
Theorem producer_death_is_invisible :
  forall (V : account -> bool) (dl : list Ev),
    V (died_after dl) = V (genuinely_short dl).
Proof. intros V dl. rewrite death_and_brevity_agree. reflexivity. Qed.

(* An L2 verifier is any predicate that rejects only on the identity. *)
Definition l2_rejects (V : account -> bool) : Prop :=
  forall x, V x = false -> ~ closes x.

(* THE SECOND RESULT. There is no log an L2 checker rejects on these grounds:
   an account produced by a dead producer always closes, so a verifier that
   rejects only non-closing accounts can never reject one. L2 has no power
   against producer death at all. *)
Theorem l2_cannot_detect_producer_loss :
  forall V dl, l2_rejects V -> V (died_after dl) <> false.
Proof.
  intros V dl HV Hfalse.
  apply HV in Hfalse. apply Hfalse. apply died_account_closes.
Qed.

(* The blindness is not about how much was lost: a producer that died after
   nothing at all is equally invisible. *)
Corollary total_death_is_invisible :
  forall V, l2_rejects V -> V (died_after []) <> false.
Proof. intros V HV. apply l2_cannot_detect_producer_loss. exact HV. Qed.

(* ======================================================================== *)
(* PART 2 -- interval attestation is the repair                             *)
(* ======================================================================== *)

(* An interval declared over ticks start .. start+k, and the tick indices an
   attestor actually witnessed. The attestor is not the producer and the
   producer cannot write to it: a producer that stops emitting does not stop
   the ticks, and the absent ticks are what its own silence cannot supply. *)
Definition ticks_present (start k : nat) (l : list nat) : bool :=
  forallb (fun i => existsb (Nat.eqb i) l) (seq start (S k)).

Definition l3i_ok (start k : nat) (l : list nat) : bool := ticks_present start k l.

(* A complete window passes. *)
Theorem full_window_passes :
  forall start k, l3i_ok start k (seq start (S k)) = true.
Proof.
  intros start k. unfold l3i_ok, ticks_present.
  apply forallb_forall. intros i Hi.
  apply existsb_exists. exists i. split; [exact Hi | apply Nat.eqb_refl].
Qed.

(* A window missing its declared start tick fails -- this is the producer
   that died before the interval began, or was never there. *)
Theorem missing_start_tick_fails :
  forall start k, l3i_ok start k (seq (S start) k) = false.
Proof.
  intros start k. unfold l3i_ok, ticks_present.
  apply Bool.not_true_iff_false. intro H.
  rewrite forallb_forall in H.
  assert (Hin : In start (seq start (S k))) by (apply in_seq; lia).
  specialize (H start Hin).
  apply existsb_exists in H. destruct H as [y [Hy Heq]].
  apply Nat.eqb_eq in Heq. subst y.
  apply in_seq in Hy. lia.
Qed.

(* A window missing any interior tick fails just the same: the level is not
   a heuristic about where the gap is. *)
Theorem missing_any_tick_fails :
  forall start k j,
    start <= j -> j <= start + k ->
    l3i_ok start k (filter (fun i => negb (Nat.eqb i j)) (seq start (S k))) = false.
Proof.
  intros start k j Hlo Hhi. unfold l3i_ok, ticks_present.
  apply Bool.not_true_iff_false. intro H.
  rewrite forallb_forall in H.
  assert (Hin : In j (seq start (S k))) by (apply in_seq; lia).
  specialize (H j Hin).
  apply existsb_exists in H. destruct H as [y [Hy Heq]].
  apply Nat.eqb_eq in Heq. subst y.
  apply filter_In in Hy. destruct Hy as [_ Hneq].
  rewrite Nat.eqb_refl in Hneq. discriminate.
Qed.

(* THE POINT OF THE WHOLE FILE. The two sessions Part 1 proved
   indistinguishable are separated the moment the interval is attested: the
   dead producer's window is missing its ticks and the short producer's is
   not, so a verdict that reads the ticks tells them apart. What L2 could not
   do with any amount of cleverness, L3i does with a witness the producer
   does not control. *)
Theorem interval_attestation_separates_them :
  forall start k,
    k > 0 ->
    l3i_ok start k (seq start (S k)) <> l3i_ok start k (seq (S start) k).
Proof.
  intros start k Hk.
  rewrite full_window_passes, missing_start_tick_fails. discriminate.
Qed.

End Interval.

(* ==========================================================================
   CORRESPONDENCE TO check_l3i.py

   The checker reads first_tick and last_tick, so k = last - first, and
   scores the interval start .. start+k. The translation, so a differential
   has something to differ from:

     ticks_present start k l    <->  the missing-tick scan in check_l3i
     full_window_passes         <->  a complete window passes VLC-L3i-2
     missing_start_tick_fails   <->  a missing first tick fails VLC-L3i-2
     missing_any_tick_fails     <->  a missing interior tick fails it too

   NOT MODELLED HERE, and therefore not proved: the binding of a tick to a
   chain position. EXT-018 found three attacks that turn on it -- a replayed
   anchor, a witness set anchored to itself, ticks bound in reverse -- and
   they are covered by executable cases in examples/l3i_cases.py and
   selftest.sh section 14, not by this development. A reader should not take
   this file as establishing more than the tick-presence result above.
   ========================================================================== *)
