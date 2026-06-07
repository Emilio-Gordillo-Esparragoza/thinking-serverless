# Contributing to thinking-serverless

Thank you for your interest in contributing to **thinking-serverless**!  
This repository is both a learning space and a collection of practical projects. All contributions (code, documentation, examples, fixes) are welcome.

Please read this guide before getting started. It ensures a smooth process and that the knowledge is well documented.

---

## Code of Conduct

This project follows a standard of respect and collaboration. Be kind, constructive, and open to ideas. Harassment or disrespect of any form will not be tolerated.

---

## Branching model and workflow

We use a two‑branch model:

- **`main`** – Production‑ready code. It only accepts merges from `canary` after final verification.
- **`canary`** – Pre‑production branch where new features are integrated and tested in an environment as close to production as possible.

The expected workflow is:

1. **Feature branch**  
   Create a branch from `main` with a descriptive name (e.g., `feat/sns-sqs-fanout`, `docs/security-zero-trust`).

2. **Open a Pull Request towards `canary`**  
   When your work is ready, open a PR targeting `canary`. Include:
   - A clear description of the change.
   - References to related issues (if any).
   - Evidence of manual or automated testing.

3. **Review and automated checks**  
   The CI workflows (`.github/workflows/`) will run linting, unit tests, and integration tests. The team will review the code, documentation, and compliance with the defined patterns.

4. **Merge to `canary`**  
   Once approved, the PR is merged into `canary`. This triggers automatic deployment to the *staging / canary* environment.

5. **Verification in the canary environment**  
   Integration tests, security validations, and (if applicable) load tests are performed in the canary environment.

6. **Promotion to `main`**  
   When everything passes, a PR from `canary` to `main` is opened. After final review, it is merged. The merge to `main` triggers deployment to production.

> **Important**: **never** push directly to `main` or `canary`. Everything goes through PR and review.

---

## Getting started

1. **Fork the repository** and clone it locally.
2. **Install dependencies** depending on the language you’ll modify:
   - Python: `pip install -r requirements-dev.txt` (or the relevant file)
   - Rust: `cargo build`
3. **Choose an infrastructure tool** to deploy locally:
   - `infrastructure/cdk/` – AWS CDK
   - `infrastructure/terraform/` – Terraform
   - `infrastructure/sam/` – AWS SAM
4. **Set up required environment variables** (see `docs/operations/` for details).

### Quick development environment setup

To speed up the installation of command‑line tools like the AWS CLI, Terraform, SAM CLI, and others, use [devtool-pack](https://github.com/Emilio-Gordillo-Esparragoza/devtool-pack).  
It provides reproducible, automated setup scripts so you can start coding faster and with fewer manual steps.

For local testing without deploying to AWS, we recommend [LocalStack](https://www.localstack.cloud/), [floci CLI](https://github.com/floci-io/floci-cli), or the SAM emulators.

---

## What can you contribute?

- **Documentation** (`docs/`): improve explanations, add new patterns, book notes, security guides, or operational procedures.
- **Examples** (`examples/`): add a minimal project that illustrates a serverless service or architectural pattern.
- **Source code** (`src/`): refactoring, test coverage, performance optimizations for Lambda functions in Python or Rust.
- **Infrastructure** (`infrastructure/`): CDK, Terraform, or SAM templates that automate deployments.
- **CI/CD** (`.github/workflows/`): pipeline improvements, new security or deployment workflows.
- **Bug fixes** or issue reporting.

---

## Code standards

- **Style**: follow the conventions of each language (PEP 8 for Python, `rustfmt` for Rust). If the project already has a linter, run it before submitting your PR.
- **Commits**: use [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat: add fan‑out SNS‑SQS pattern`, `docs: improve IAM guide`). This helps generate changelogs automatically.
- **Tests**: all new code must include unit tests (and integration tests where applicable). If you fix a bug, add a test that reproduces it.
- **Documentation**: update the `README.md` or the docs in `docs/` if your change affects how the project is used. Functions should have clear docstrings explaining the “why”.
- **Examples**: if you create a new example, include a small `README.md` inside its folder explaining which pattern it demonstrates and how to run it.

---

## Reporting issues

If you find a bug or have an idea for improvement:

1. Search the [existing issues](https://github.com/Emilio-Gordillo-Esparragoza/thinking-serverless/issues) to avoid duplicates.
2. Create a new issue with:
   - A clear title.
   - Steps to reproduce (if a bug).
   - Expected vs actual behavior.
   - Screenshots or code snippets if helpful.
3. Suggested labels: `bug`, `enhancement`, `documentation`, `good first issue`.

---

## Pull Request process

1. **Create your branch** from `main` (e.g., `fix/api-gateway-security`).
2. **Develop and test** locally.
3. **Push the branch** to your fork and open a PR towards `canary`.
4. In the PR, include:
   - What problem does it solve?
   - How does it solve it?
   - What tests did you perform?
   - Screenshots or diagrams if the change is visual.
   - Reference to the issue (e.g., `Closes #12`).
5. The team will review and request changes if needed. Be receptive and open to discussion.
6. Once approved and merged to `canary`, it will be tested in the canary environment. If all checks pass, it will be promoted to `main` via another PR.

---

## Development and deployment environments

The environments are defined in `.github/workflows/`:

- **`deploy-dev.yml`**: deploys to the development environment (likely using the `canary` branch).
- **`deploy-prod.yml`**: deploys to production from `main`.

If you want to run the pipelines in your own fork, you’ll need to configure the corresponding secrets (AWS credentials, etc.). See `docs/operations/` for details.

---

## License

By contributing, you agree that your code will be distributed under the same license as the project (see `LICENSE` file). If you are unsure about anything, ask in an issue or discussion.

---

Thank you for helping make **thinking-serverless** a useful reference for the community!  
If you have questions about the process, open an issue with the `question` label.