import numpy as np

from ass2.random_forest_constants import *


# a.k.a. bagging_random_datasets
def bootstrap(df):
    datasets = []
    for _ in range(BAGGING_RANDOM_FOREST_SET_AMOUNT):
        # replace=True means an element can be chosen multiple times.
        sampled_data = df.sample(n=BAGGING_RANDOM_FOREST_SET_SIZE, replace=True, random_state=RANDOM_SEED)
        datasets.append(sampled_data)
    return datasets


class RandomForest:
    def __init__(self, n_trees):
        self.n_trees = n_trees
        self.trees = []

    def fit(self, df):
        # Generate bootstrapped datasets and train trees
        datasets = bootstrap(df)
        for dataset in datasets:
            tree = TreeNode()
            tree.train(dataset)
            self.trees.append(tree)

    def predict(self, x):
        # Aggregate predictions from all trees
        predictions = [tree.predict(x) for tree in self.trees]
        return np.mean(predictions)


class TreeNode:
    def __init__(self, depth=0):
        self.left = None
        self.right = None
        self.feature = None
        self.split_value = None
        self.is_leaf = False
        self.mean_value = None
        self.depth = depth

    def calculate_se_on_split(self, df, mean):
        return ((df['Target'] - mean) ** 2).sum()

    def calculate_single_sse_on_split(self, df):
        mean = df['Target'].mean()
        return self.calculate_se_on_split(df, mean)

    def calculate_total_sse_on_split(self, df, feature, mean_value):
        left_sse = self.calculate_single_sse_on_split(df[df[feature] <= mean_value])
        right_sse = self.calculate_single_sse_on_split(df[df[feature] > mean_value])
        return left_sse + right_sse

    def find_best_split(self, df, feature):
        # ([1,2,3][:-1] + [1,2,3][1:]) / 2
        # ([1,2] + [2,3]) / 2
        # [3,5] / 2
        # [1.5,2.5]
        means = (df[feature].values[:-1] + df[feature].values[1:]) / 2
        best_sse = float('inf')
        best_split = None

        for mean in means:
            total_sse = self.calculate_total_sse_on_split(df, feature, mean)
            if total_sse < best_sse:
                best_sse = total_sse
                best_split = mean

        return best_split, best_sse

    def train(self, df):
        """
        Call this function after the Tree node creation.

        This function determines:
         the node type, if it is the leaf or tree.
         the node mean value, which is mean of target. It is non-null only by leaf.
         the best feature which provides the most fine-grade tuning.
         the split value which tells if you found the node, or you need to traverse left or right.
         the left and right nodes in case the current node is a tree.

        :param df: is the dataset we are training on
        """
        if self.depth >= MAX_TREE_DEPTH or len(df) < 2:
            self.is_leaf = True
            self.mean_value = df['Target'].mean()
            return

        # Choose the best feature and split value
        best_feature = None
        best_split = None
        best_sse = float('inf')

        for feature in df.drop(columns=['Target']).columns:
            sorted_df = df[[feature, 'Target']].sort_values(by=feature)
            split, sse = self.find_best_split(sorted_df, feature)

            if sse < best_sse:
                best_sse = sse
                best_feature = feature
                best_split = split

        if best_feature is None or best_split is None:
            self.is_leaf = True
            self.mean_value = df['Target'].mean()
            return

        self.feature = best_feature
        self.split_value = best_split

        # Create child nodes
        left_data = df[df[best_feature] <= best_split]
        right_data = df[df[best_feature] > best_split]

        self.left = TreeNode(depth=self.depth + 1)
        self.right = TreeNode(depth=self.depth + 1)

        # Recursively fit child nodes
        self.left.train(left_data)
        self.right.train(right_data)

    def predict(self, x):
        if self.is_leaf:
            return self.mean_value
        if x[self.feature] <= self.split_value:
            return self.left.predict(x)
        return self.right.predict(x)
