(* ==========================================================================
   sentinel_interval.v — the producer-death gap, and the interval coverage
   level that closes it.

   FINDING CREDIT. Both results below state a defect reported by
   Shahab K. against VLC-1 on 2026-09-13, reproduced against the published
   conformance checker and the published example corpus. The defect is his;
   the formalisation is the response to it.

   The substantive theorem is producer_death_is_invisible. VLC-1's L2 requires
   that gaps be DECLARED in-log. That requirement presupposes something the
   specification never states: that the producer survived to write the
   declaration. If the producer is what failed, no records are produced, no
   loss is declared, and the delivered file is internally perfect over whatever
   window it happens to cover.

   The opening paragraph of the specification — a two-hour outage being
   indistinguishable from a quiet afternoon — is therefore established only for
   TRANSPORT loss. For producer loss it is not merely undetected; the truncated
   log and the honest log are the same object to the checker.
   ========================================================================== *)

Require Import List Arith Bool Lia.
Import ListNotations.

(* ------------------------------------------------------------- the records *)
Inductive Rec : Set :=
| Obs  (n : nat)            (* an observation carrying the producer's counter *)
| Loss (from to : nat).     (* an in-log declaration of an unserved interval *)

Definition Log := list Rec.

(* The L2 completeness identity, exactly as the checker computes it: observed
   counters and declared intervals must be gapless from the expected start. *)
Fixpoint closes (expect : nat) (l : Log) : bool :=
  match l with
  | [] => true
  | Obs n :: rest => if Nat.eqb n expect then closes (S n) rest else false
  | Loss f t :: rest => if Nat.eqb f expect then closes (S t) rest else false
  end.

(* Renumbering: what a producer that restarted from zero emits, and equally
   what an adversary does to a truncated file to make the identity close. *)
Fixpoint renumber (next : nat) (l : Log) : Log :=
  match l with
  | [] => []
  | Obs _ :: rest => Obs next :: renumber (S next) rest
  | Loss _ _ :: rest => Loss next next :: renumber (S next) rest
  end.

(* ===================================================== the finding, proved *)

Lemma renumber_closes : forall l k, closes k (renumber k l) = true.
Proof.
  induction l as [| r rest IH]; intros k.
  - reflexivity.
  - destruct r as [n | f t]; simpl; rewrite Nat.eqb_refl; apply IH.
Qed.

(* Any suffix of any log, renumbered, satisfies the identity. *)
Theorem renumbered_suffix_closes :
  forall (pre suf : Log), closes 0 (renumber 0 suf) = true.
Proof. intros pre suf. apply renumber_closes. Qed.

(* THE FINDING (Shahab K., 2026-09-13).

   A checker's verdict on a renumbered truncation is EQUAL to its verdict on
   the renumbered whole. Not similar, not weaker — equal. Records may be
   discarded wholesale and the delivered file remains, to the identity,
   indistinguishable from a complete one. No declaration is required because
   the producer that would have written one is what failed. *)
Theorem producer_death_is_invisible :
  forall (pre suf : Log),
    closes 0 (renumber 0 (pre ++ suf)) = closes 0 (renumber 0 suf).
Proof.
  intros pre suf.
  rewrite (renumber_closes (pre ++ suf) 0), (renumber_closes suf 0).
  reflexivity.
Qed.

(* Stated the other way, because this is the form that matters to a reader:
   there is no log an L2 checker rejects on these grounds. L2 has no power
   against producer death at all. *)
Corollary l2_cannot_detect_producer_loss :
  forall l, closes 0 (renumber 0 l) = true.
Proof. intro l. apply renumber_closes. Qed.

(* ================================================ L3i — interval coverage *)
(* The repair. Coverage is declared over an INTERVAL, and every tick in that
   interval is witnessed by an attestor the producer does not control. A
   producer that dies stops producing ticks, and the missing ticks are the
   evidence its own silence could not supply. *)

Inductive Rec3 : Set :=
| Obs3  (n : nat)
| Loss3 (from to : nat)
| Tick  (i : nat).          (* attestor-witnessed interval tick *)

Definition Log3 := list Rec3.

Fixpoint has_tick (i : nat) (l : Log3) : bool :=
  match l with
  | [] => false
  | Tick j :: rest => if Nat.eqb i j then true else has_tick i rest
  | _ :: rest => has_tick i rest
  end.

(* Every tick from start to start+k must be present. *)
Fixpoint ticks_present (start k : nat) (l : Log3) : bool :=
  match k with
  | 0 => has_tick start l
  | S k' => andb (has_tick start l) (ticks_present (S start) k' l)
  end.

Definition l3i_ok (start k : nat) (l : Log3) : bool := ticks_present start k l.

(* A log with no tick for the declared start fails, whatever else it contains
   and however its counters are renumbered. Silence is now a finding. *)
Theorem missing_start_tick_fails :
  forall start k l,
    has_tick start l = false ->
    l3i_ok start k l = false.
Proof.
  intros start k l H. unfold l3i_ok. destruct k; simpl; rewrite H; reflexivity.
Qed.

Definition full_window (start k : nat) : Log3 :=
  map (fun i => Tick (start + i)) (seq 0 (S k)).

Lemma has_tick_in : forall j l, In (Tick j) l -> has_tick j l = true.
Proof.
  intros j l. induction l as [| r rest IH]; simpl; [contradiction |].
  intros [Heq | Hin].
  - subst. rewrite Nat.eqb_refl. reflexivity.
  - destruct r as [n | f t | i].
    + apply IH, Hin.
    + apply IH, Hin.
    + destruct (Nat.eqb j i); [reflexivity | apply IH, Hin].
Qed.

Lemma window_has : forall start k j,
  start <= j -> j <= start + k -> has_tick j (full_window start k) = true.
Proof.
  intros start k j H1 H2. apply has_tick_in. unfold full_window.
  assert (Heq : j = start + (j - start)) by lia.
  rewrite Heq at 1.
  apply (in_map (fun i : nat => Tick (start + i)) (seq 0 (S k)) (j - start)).
  apply in_seq. lia.
Qed.

(* And the honest case still passes, so the level is not vacuous. *)
Theorem full_window_passes : forall start k, l3i_ok start k (full_window start k) = true.
Proof.
  intros start k. unfold l3i_ok.
  assert (forall k' d, k' + d = k -> ticks_present (start + d) k' (full_window start k) = true) as H.
  { induction k' as [| k'' IH]; intros d Hd.
    - cbn [ticks_present]. apply window_has; lia.
    - cbn [ticks_present]. rewrite (window_has start k (start + d)) by lia.
      cbn [andb].
      replace (S (start + d)) with (start + S d) by lia.
      apply IH. lia. }
  specialize (H k 0). replace (start + 0) with start in H by lia. apply H. lia.
Qed.

Print Assumptions producer_death_is_invisible.
Print Assumptions missing_start_tick_fails.

(* ==========================================================================
   APPENDIX, added 2026-09-27 (EXT-019). Everything above this line is the
   original development, restored verbatim: 8 results, the count
   CORRIGENDUM-2026-09-13-01.md printed. It was cited in five places and
   absent from the repository for two weeks; see EXT-019 for how that
   happened and why nothing caught it.

   One result is added, and one only, because the rest of what a replacement
   attempt produced that day was either already here or weaker than what is
   here. missing_start_tick_fails covers a missing tick at the declared
   start. The checker's scan does not privilege the start, so the interior
   case deserves to be stated too: a level that only caught gaps at the edge
   would be a different and much weaker level.
   ========================================================================== *)

Theorem missing_any_tick_fails :
  forall start k l j,
    start <= j -> j <= start + k ->
    has_tick j l = false ->
    l3i_ok start k l = false.
Proof.
  intros start k. revert start.
  induction k as [| k' IH]; intros start l j H1 H2 Hno.
  - unfold l3i_ok. simpl. assert (j = start) by lia. subst. exact Hno.
  - unfold l3i_ok in *. simpl.
    destruct (Nat.eq_dec j start) as [Heq | Hne].
    + subst. rewrite Hno. reflexivity.
    + rewrite (IH (S start) l j); [apply Bool.andb_false_r | lia | lia | exact Hno].
Qed.

Print Assumptions missing_any_tick_fails.
