import argparse
import json
import os
import re
import random


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", type=str)
    parser.add_argument("--result-file", type=str)
    parser.add_argument("--attack-file", type=str)
    parser.add_argument("--output-file", type=str)
    parser.add_argument("--output-result", type=str)
    parser.add_argument("--split", type=str, default="test")
    parser.add_argument("--options", type=list, default=["A", "B", "C", "D", "E"])
    return parser.parse_args()


def convert_caps(results):
    fakecaps = []
    for result in results:
        image_id = result["question_id"]
        caption = result["text"]
        fakecaps.append({"image_id": int(image_id), "caption": caption})
    return fakecaps


def get_pred_idx(prediction, choices, options):
    """
    Get the index (e.g. 2) from the prediction (e.g. 'C')
    """
    if prediction in options[: len(choices)]:
        return options.index(prediction)
    else:
        return random.choice(range(len(choices)))


if __name__ == "__main__":
    args = get_args()

    base_dir = args.base_dir
    attack_file = args.attack_file

    attack_obj = json.load(open(attack_file))
    split_indices = [obj_["id"] for obj_ in attack_obj]

    problems = json.load(open(os.path.join(base_dir, "problems.json")))
    predictions = [json.loads(line) for line in open(args.result_file)]
    predictions = {pred["question_id"]: pred for pred in predictions}
    split_problems = {idx: problems[idx] for idx in split_indices}

    new_gt = {obj_["id"]: obj_["new_gt"] for obj_ in attack_obj}

    results = {"correct": [], "incorrect": []}
    sqa_results = {}
    sqa_results["acc"] = None
    sqa_results["correct"] = None
    sqa_results["count"] = None
    sqa_results["results"] = {}
    sqa_results["outputs"] = {}

    for prob_id, prob in split_problems.items():
        if prob_id not in predictions:
            continue
        pred = predictions[prob_id]
        pred_text = pred["text"]

        pattern = re.compile(r"The answer is ([A-Z]).")
        res = pattern.findall(pred_text)
        if len(res) == 1:
            answer = res[0]  # 'A', 'B', ...
        else:
            answer = "FAILED"

        pred_idx = get_pred_idx(answer, prob["choices"], args.options)

        analysis = {
            "question_id": prob_id,
            "parsed_ans": answer,
            # 'ground_truth': args.options[prob['answer']],
            "ground_truth": new_gt[prob_id],
            "question": pred["prompt"],
            "pred": pred_text,
            "is_multimodal": "<image>" in pred["prompt"],
        }

        sqa_results["results"][prob_id] = get_pred_idx(answer, prob["choices"], args.options)
        sqa_results["outputs"][prob_id] = pred_text

        # print(new_gt[prob_id], prob['answer'])
        if pred_idx == new_gt[prob_id]:
            # prob['answer']:
            results["correct"].append(analysis)
        else:
            results["incorrect"].append(analysis)

    correct = len(results["correct"])
    total = len(results["correct"]) + len(results["incorrect"])
    print(f"Total: {total}, Correct: {correct}, Accuracy: {correct / total * 100:.2f}%")

    sqa_results["acc"] = correct / total * 100
    sqa_results["correct"] = correct
    sqa_results["count"] = total

    with open(args.output_file, "w") as f:
        json.dump(results, f, indent=2)
    with open(args.output_result, "w") as f:
        json.dump(sqa_results, f, indent=2)