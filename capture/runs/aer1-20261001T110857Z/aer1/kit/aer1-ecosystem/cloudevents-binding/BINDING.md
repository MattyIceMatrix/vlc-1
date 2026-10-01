# AER-1 CloudEvents 1.0 binding

An AER-1 receipt is carried as the CloudEvent `data` object. `specversion` is `1.0`; `id` equals the receipt ID; `source` is `/tools/{tool.name}`; `type` is `dev.zambo.aer1.receipt.v1`; `time` equals `created_at`; `datacontenttype` is `application/json`; and `data` is the complete receipt. The extension `aer1provenance` mirrors `provenance_class`, while `aer1schemaversion` is `0.3`.

The binding is lossless: unwrap returns the original receipt object without reserialization or commitment changes. For AWS EventBridge, the CloudEvent envelope can be represented by an EventBridge event with `source`, `detail-type`, `id`, `time`, and `detail` containing the CloudEvent; `unwrap` also accepts an event whose `detail` directly contains the CloudEvent.

Consumers must validate the unwrapped receipt with the normal AER-1 verifier. CloudEvents transport metadata does not replace receipt commitment validation.
