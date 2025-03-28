const { ethers } = require("ethers");
const fs = require("fs");

async function main() {
    // 1. 从 verifier.json 读取部署信息
    const verifierJSON = JSON.parse(fs.readFileSync("./build/contracts/verifier.json", "utf8"));
    const verifierNetworks = verifierJSON.networks;
    const verifierNetworkIDs = Object.keys(verifierNetworks);
    if (verifierNetworkIDs.length === 0) {
        console.error("Error: verifier.json 中没有找到已部署的网络信息");
        process.exit(1);
    }
    const verifierAddress = verifierNetworks[verifierNetworkIDs[0]].address;
    const verifierAbi = verifierJSON.abi;
    if (!verifierAddress || !verifierAbi) {
        console.error("Error: 无法从 verifier.json 中提取地址或 ABI 信息");
        process.exit(1);
    }
    console.log("Verifier 合约地址:", verifierAddress);

    // 2. 从 VideoNFT.json 读取部署信息
    const videoNFTJSON = JSON.parse(fs.readFileSync("./build/contracts/VideoNFT.json", "utf8"));
    const videoNFTNetworks = videoNFTJSON.networks;
    const videoNFTNetworkIDs = Object.keys(videoNFTNetworks);
    if (videoNFTNetworkIDs.length === 0) {
        console.error("Error: VideoNFT.json 中没有找到已部署的网络信息");
        process.exit(1);
    }
    const videoNFTAddress = videoNFTNetworks[videoNFTNetworkIDs[0]].address;
    const videoNFTAbi = videoNFTJSON.abi;
    if (!videoNFTAddress || !videoNFTAbi) {
        console.error("Error: 无法从 VideoNFT.json 中提取地址或 ABI 信息");
        process.exit(1);
    }
    console.log("VideoNFT 合约地址:", videoNFTAddress);

    // 3. 从 proof.json 读取证明数据
    const proofData = JSON.parse(fs.readFileSync("proof.json", "utf8"));
    const proof = proofData.proof;
    const inputs = proofData.inputs;
    if (!proof || !inputs) {
        console.error("Error: proof.json 格式不正确，必须包含 proof 和 inputs 字段");
        process.exit(1);
    }

    // 4. 从 uploadResult.json 读取视频上传结果，取 cid 构造 tokenURI
    const uploadResult = JSON.parse(fs.readFileSync("uploadResult.json", "utf8"));
    const cid = uploadResult.cid;
    if (!cid) {
        console.error("Error: uploadResult.json 中未找到 cid 字段");
        process.exit(1);
    }
    const tokenURI = "ipfs://" + cid;
    console.log("使用的 tokenURI:", tokenURI);

    // 5. 连接到以太坊节点，并实例化合约对象
    const provider = new ethers.providers.JsonRpcProvider("http://localhost:8545");
    const signer = provider.getSigner(); // 注意：必须为 VideoNFT 合约的 owner

    const verifierContract = new ethers.Contract(verifierAddress, verifierAbi, signer);
    const videoNFTContract = new ethers.Contract(videoNFTAddress, videoNFTAbi, signer);

    // 6. 调用 verifier 合约验证证明
    console.log("正在验证证明...");
    let isValid;
    try {
        isValid = await verifierContract.verifyTx(
            proof,
            inputs   // 公共输入数组
        );
        console.log("证明验证结果:", isValid);
    } catch (error) {
        console.error("验证证明时出错:", error);
        process.exit(1);
    }

    if (!isValid) {
        console.error("证明验证失败，NFT 铸造中止");
        process.exit(1);
    }

    // 7. 调用 VideoNFT 合约铸造 NFT，使用 tokenURI
    try {
        console.log("正在铸造 NFT...");
        const ownerAddress = await signer.getAddress();
        const tx = await videoNFTContract.mintVideoNFT(ownerAddress, tokenURI);
        console.log("铸造交易已发送，交易哈希:", tx.hash);
        const receipt = await tx.wait();
        console.log("NFT 铸造成功，交易回执:", receipt);
    } catch (error) {
        console.error("铸造 NFT 时出错:", error);
        process.exit(1);
    }
}

main();
