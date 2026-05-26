# Legal and Support Pack

This folder contains the source-of-truth legal and support markdown for Story
Generator.

These files are rendered into the shipped app's legal and trust surfaces and
should stay aligned with the current product behavior: FastAPI auth, local or
configured object-backed asset storage, OpenAI-backed generation, moderation,
account/billing support, and repository-maintained support workflows.

Policy docs
- [Privacy Policy](privacy-policy.md)
- [Terms of Service](terms-of-service.md)
- [Acceptable Use / Content Policy](acceptable-use-policy.md)
- [Copyright and IP Policy](copyright-ip-policy.md)
- [Support / Contact Policy](support-policy.md)
- [Privacy Operations](privacy-operations.md)
- [Subprocessors And Service Providers](subprocessors.md)
- [AI Processing Disclosure](ai-processing-disclosure.md)

Notes
- This folder is the canonical source for the legal/support copy shown by the
  app.
- These documents are intentionally maintained in-repo.
- Refund guidance is now covered in this folder. DPA terms and broader
  commercial commitments remain out of scope for this repository pass.
- The subprocessors list here is intentionally narrow and reflects the current
  repo baseline rather than future commercial infrastructure.