const { ethers } = require("ethers");
const fs = require("fs");

async function main() {
    // 读取 verifier.json 文件
    const verifierJSON = JSON.parse(fs.readFileSync("build/contracts/verifier.json", "utf8"));

    // 从 networks 字段中提取部署信息
    const networks = verifierJSON.networks;
    const networkIDs = Object.keys(networks);
    if (networkIDs.length === 0) {
        console.error("Error: verifier.json 中没有找到已部署的网络信息");
        process.exit(1);
    }
    // 这里选择第一个网络的部署信息
    const contractAddress = networks[networkIDs[0]].address;
    if (!contractAddress) {
        console.error("Error: 在 verifier.json 的 networks 中未找到合约地址");
        process.exit(1);
    }
    console.log("使用的合约地址:", contractAddress);

    // 读取 ABI 信息
    const verifierAbi = verifierJSON.abi;
    if (!verifierAbi) {
        console.error("Error: verifier.json 中未找到 ABI 信息");
        process.exit(1);
    }

    // 读取 proof.json 文件，提取 proof 数据和公共输入
    const proofData = JSON.parse(fs.readFileSync("proof.json", "utf8"));
    const proof = proofData.proof;
    const inputs = proofData.inputs;
    if (!proof || !inputs) {
        console.error("Error: proof.json 格式不正确，必须包含 proof 和 inputs 字段");
        process.exit(1);
    }

    // 连接到以太坊节点（例如本地 Ganache 节点）
    const provider = new ethers.providers.JsonRpcProvider("http://localhost:8545");
    const signer = provider.getSigner();

    // 创建 verifier 合约实例
    const verifierContract = new ethers.Contract(contractAddress, verifierAbi, signer);

    console.log("开始调用 verifier 合约进行验证...");

    try {
        // 调用 verifyTx 方法（假设参数顺序为：proof.A, proof.B, proof.C, inputs）
        const result = await verifierContract.verifyTx(
            proof,
            inputs         // 公共输入数组
        );
        console.log("验证结果：", result);
    } catch (error) {
        console.error("调用 verifier 合约时出错：", error);
    }
}

main();
