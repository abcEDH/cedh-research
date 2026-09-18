# Backend Model Artifacts

Tracked production model artifacts live here. Generated training reports, scratch
evaluations, and experiment outputs should stay under `packages/backend/reports/`,
which is ignored by git.

Runtime simulator defaults should point to this directory when the deployed app
must load an artifact from the repository checkout.

## v4 hybrid runtime

The v4 pod-outcome artifact supplies only the draw probability. Decisive winner
shares use the versioned internal Elo model, including separate Swiss and top-cut
seat adjustments. The selected features exclude displayed TopDeck Elo.

The artifact was trained with scikit-learn 1.7.2; the backend pins that version.
`model_artifacts.py` resolves the training build's unqualified `_loss` Cython
module to `sklearn._loss._loss` when reading trusted artifacts. The production
artifact is loaded and exercised in `test_pod_outcome_model.py`.

The Next.js streaming endpoint is deferred to PR #297. Backend CLI streaming
remains available; merging the model does not deploy a Python web service.
