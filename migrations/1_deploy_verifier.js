const Verifier = artifacts.require("Verifier");

module.exports = function (deployer) {
    // 提供较高的 gas 限额以防止部署过程中 gas 不足
    deployer.deploy(Verifier, { gas: 5000000 });
};
